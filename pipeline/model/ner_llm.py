
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from ..core.config import Settings
from ..core.deployment import ORGAO_GOVERNO_CURTO, ORGAOS_ACRONIMOS, TRIBUNAL_EXEMPLO

log = logging.getLogger(__name__)


PROVENANCE_VALUES = {"gliner", "llm", "hybrid"}

NER_SHORT_LABELS = (
    "pessoa", "pessoa_juridica", "orgao", "cargo",
    "email", "cpf", "cnpj", "matricula",
    "data", "valor_monetario", "endereco", "telefone",
    "numero_processo", "lei", "decreto", "portaria",
    "contrato_edital", "assunto", "objeto_licitacao", "vigencia", "url",
)


_LLM_EXTRACT_SYSTEM = """Você é um extrator de entidades nomeadas (NER) especializado em \
documentos administrativos do {ORGAO_GOVERNO_CURTO} (sistema SEI).

Para cada entidade extraída, retorne JSON com:
- "text": texto exato como aparece no documento
- "canonical": forma canônica preferida (ex: nome completo expandido, sigla expandida)
- "provenance": "llm" (sempre, nesta operação)

Regras críticas:
1. NÃO classifique papéis genéricos como pessoas: "CONTRATANTE", "CONTRATADA", \
"licitante", "adjudicatário", "Senhor (a)", "Excelentíssimo" NÃO são pessoas.
2. CPFs com máscara ("xxx.xxx.xxx-NN") devem ser IGNORADOS (não extraídos).
3. Acrônimos de leis (LGPD, LRF, CLT) NÃO são órgãos — classifique como "lei".
4. Acrônimos de órgãos ({ORGAOS_ACRONIMOS}) podem ser classificados como "orgao", \
mas em "canonical" inclua o nome expandido quando óbvio (ex: TJPI → \
"{TRIBUNAL_EXEMPLO}").
5. Consolide variantes da mesma entidade dentro do mesmo documento — não \
retorne "Maria Silva" e "MARIA SILVA" como entradas separadas.
6. Fragmentos truncados (menos de 6 caracteres OU palavras incompletas) \
devem ser DESCARTADOS.

Retorne APENAS JSON válido no schema solicitado, sem texto adicional.""".replace("{ORGAO_GOVERNO_CURTO}", ORGAO_GOVERNO_CURTO).replace("{ORGAOS_ACRONIMOS}", ORGAOS_ACRONIMOS).replace("{TRIBUNAL_EXEMPLO}", TRIBUNAL_EXEMPLO)

_LLM_CONSOLIDATE_SYSTEM = """Você é um consolidador de entidades NER. Receberá:

1. O TEXTO completo do documento.
2. Um output preliminar de NER (do GLiNER2) com possíveis erros.

Sua tarefa: limpar e consolidar o output preliminar. Retorne JSON com o \
mesmo formato, mas:

- Remova falsos positivos (papéis genéricos como CONTRATANTE, fragmentos \
truncados como "VALDY DE MOURA FE" ou "Secretaria da Faz", máscaras de CPF \
"xxx.xxx.xxx-NN").
- Consolide variantes da mesma entidade (case, typos, abbreviations).
- Reclassifique labels obviamente errados (ex: "LGPD" classificada como \
órgão deve virar "lei").
- Adicione "canonical" expandindo siglas conhecidas.
- Marque cada entidade resultante com "provenance": "llm" se foi adicionada/\
modificada, ou "gliner" se foi mantida intacta do input.

Para cada entidade modificada/adicionada, justifique brevemente em \
"_audit" (apenas para auditoria; pode ser omitido em produção).

Retorne APENAS JSON válido."""


_OUTPUT_SCHEMA_HINT = {
    "entities": {
        "<label>": [
            {"text": "<exact span>", "canonical": "<preferred form>", "provenance": "llm"},
        ],
    },
    "classification": {"tipo_documento": "<type>"},
    "relations": {},
}


class NerLLMError(RuntimeError):
    pass


class NerLLMSchemaError(NerLLMError):
    pass


@dataclass
class NerLLMConfig:
    base_url: str
    api_key: str
    model: str = "soberano-alpha"
    timeout_s: int = 120
    temperature: float = 0.1
    max_retries: int = 3
    backoff_base: float = 1.5
    backoff_max: float = 30.0


def config_from_settings(settings: Settings, *, model: str | None = None) -> NerLLMConfig:
    chosen_model = model or settings.openai_model_ner or settings.openai_model_texto or settings.openai_model or "soberano-alpha"
    return NerLLMConfig(
        base_url=settings.openai_base_url, api_key=settings.openai_api_key, model=chosen_model)


class NerLLM:

    def __init__(self, config: NerLLMConfig) -> None:
        self.config = config
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "EMPTY",
            timeout=httpx.Timeout(float(config.timeout_s), connect=10.0),
        )

    def extract(
        self,
        text: str,
        *,
        labels: tuple[str, ...] = NER_SHORT_LABELS,
    ) -> dict[str, Any]:
        user_msg = (
            f"Extraia entidades do texto abaixo. Use APENAS estas labels: "
            f"{', '.join(labels)}.\n\n"
            f"Schema esperado: {json.dumps(_OUTPUT_SCHEMA_HINT, ensure_ascii=False)}\n\n"
            f"Texto:\n---\n{text}\n---"
        )
        return self._chat_json(_LLM_EXTRACT_SYSTEM, user_msg)

    def consolidate(
        self,
        text: str,
        gliner_output: dict[str, Any],
    ) -> dict[str, Any]:
        gliner_summary = json.dumps(
            {
                "entities": gliner_output.get("entities", {}),
                "classification": gliner_output.get("classification", {}),
            },
            ensure_ascii=False,
        )
        user_msg = (
            f"Texto do documento:\n---\n{text}\n---\n\n"
            f"Output preliminar do GLiNER2 (limpe e consolide):\n"
            f"```json\n{gliner_summary}\n```\n\n"
            f"Retorne JSON no MESMO schema (entities por label, classification, "
            f"relations). Mantenha label do GLiNER quando correta; mude apenas "
            f"quando claramente errada."
        )
        return self._chat_json(_LLM_CONSOLIDATE_SYSTEM, user_msg)

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        last_err: Exception | None = None
        last_raw: str | None = None
        for attempt in range(self.config.max_retries):
            try:
                resp = self._client.chat.completions.create(
                    model=self.config.model,
                    messages=self._build_messages(system, user, last_raw, last_err),
                    temperature=self.config.temperature,
                    response_format={"type": "json_object"},
                )
                last_raw = resp.choices[0].message.content or ""
                parsed = json.loads(last_raw)
                if not isinstance(parsed, dict) or "entities" not in parsed:
                    raise NerLLMSchemaError(
                        "JSON missing required key 'entities'"
                    )
                return parsed
            except (RateLimitError, APITimeoutError, APIError) as e:
                last_err = e
                wait = min(
                    self.config.backoff_base ** attempt + random.random(),
                    self.config.backoff_max,
                )
                log.warning(
                    "ner-llm transient error (attempt %d/%d): %s — retry in %.1fs",
                    attempt + 1, self.config.max_retries, e, wait,
                )
                time.sleep(wait)
            except (json.JSONDecodeError, NerLLMSchemaError) as e:
                last_err = e
                log.warning(
                    "ner-llm schema error (attempt %d/%d): %s — will re-prompt",
                    attempt + 1, self.config.max_retries, e,
                )
        raise NerLLMError(
            f"ner-llm failed after {self.config.max_retries} attempts: {last_err}"
        )

    @staticmethod
    def _build_messages(
        system: str,
        user: str,
        last_raw: str | None,
        last_err: Exception | None,
    ) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if last_raw and last_err:
            msgs.append({"role": "assistant", "content": last_raw})
            msgs.append({
                "role": "user",
                "content": (
                    f"O JSON anterior é inválido: {last_err}. "
                    f"Retorne APENAS JSON válido seguindo o schema."
                ),
            })
        return msgs


def normalize_entity_record(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        return {"text": item, "canonical": item, "provenance": "gliner"}
    if isinstance(item, dict):
        text = item.get("text") or item.get("entity") or ""
        canonical = item.get("canonical") or text
        provenance = item.get("provenance") or "gliner"
        if provenance not in PROVENANCE_VALUES:
            provenance = "gliner"
        return {"text": text, "canonical": canonical, "provenance": provenance}
    return {"text": str(item), "canonical": str(item), "provenance": "gliner"}


def diff_metrics(
    before: dict[str, list],
    after: dict[str, list],
) -> dict[str, int]:
    def _flat(d: dict[str, list]) -> set[tuple[str, str]]:
        out: set[tuple[str, str]] = set()
        for label, items in (d or {}).items():
            for it in items:
                rec = normalize_entity_record(it)
                out.add((label, rec["text"].strip().lower()))
        return out

    b = _flat(before)
    a = _flat(after)
    dropped = len(b - a)
    added = len(a - b)
    kept = len(b & a)
    relabeled = 0
    by_text_before: dict[str, set[str]] = {}
    by_text_after: dict[str, set[str]] = {}
    for label, text in b:
        by_text_before.setdefault(text, set()).add(label)
    for label, text in a:
        by_text_after.setdefault(text, set()).add(label)
    for text, labels_b in by_text_before.items():
        labels_a = by_text_after.get(text, set())
        if labels_a and labels_a != labels_b:
            relabeled += 1
    return {
        "gliner_entity_count": len(b),
        "llm_dropped_count": dropped,
        "llm_added_count": added,
        "llm_kept_count": kept,
        "llm_relabeled_count": relabeled,
    }
