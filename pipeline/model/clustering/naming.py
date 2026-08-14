
from __future__ import annotations

import json
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .._result import ClusterCatalog
from .catalog import _category_id



from ...core.deployment import ORGAO_GOVERNO, ORGAO_SUFIXO

log = logging.getLogger(__name__)



__all__ = ["compute_dbcv"]


NAMING_SYSTEM_PROMPT = """\
Você categoriza processos administrativos do {ORGAO_GOVERNO} (sistema SEI). \
Recebe uma amostra de processos de UMA categoria emergente (clustering não-supervisionado). \
Para cada processo a amostra traz, quando disponível: o tópico e o resumo do documento inicial, \
as unidades por onde passou e os tipos de ação.

Dê à categoria um nome ESPECÍFICO e DISTINTIVO, ancorado PRIMEIRO nas palavras-chave \
mais frequentes da categoria (quando fornecidas), depois nos tópicos/resumos dos documentos, \
nas unidades e nos tipos de ação — um nome que permita DIFERENCIAR esta categoria de outras \
parecidas. NÃO use a classificação oficial do SEI: a categoria deve emergir do conteúdo e do \
fluxo observados, não do rótulo declarado. Regras:
- Use o assunto concreto (ex.: "Licitação por pregão eletrônico", "Contratação de estagiário", \
"Concessão de diárias e passagens", "Progressão funcional de servidor", "Inexigibilidade de licitação").
- EVITE rótulos genéricos e intercambiáveis como "Gestão de Procedimentos", "Gestão Administrativa", \
"Solicitação de Pessoal" sozinhos — eles não distinguem nada.
- Escreva em PORTUGUÊS COMPLETO e natural, COM artigos e preposições (ex.: "Adesão a Ata de Registro \
de Preços", "Pagamento de Serviços Terceirizados de Mão de Obra", "Concessão de Diárias e Passagens"). \
NUNCA abrevie nem omita preposições/artigos — evite formas telegráficas como "Adesão Ata Registro Preços". \
Use quantas palavras forem necessárias para ficar claro e gramaticalmente correto (tipicamente 4 a 10 \
palavras), sem o sufixo do órgão (não termine em "{ORGAO_SUFIXO}").

Forneça também: uma descrição factual de 1 frase, e 3 marcadores que distinguem esta categoria \
(palavras-chave do tópico, unidade característica, tipo de documento).

Retorne APENAS JSON válido neste schema:

{
  "nome": "string",
  "descricao": "string",
  "marcadores": ["string", "string", "string"]
}
""".replace("{ORGAO_GOVERNO}", ORGAO_GOVERNO).replace("{ORGAO_SUFIXO}", ORGAO_SUFIXO)


def _format_sample(p: dict) -> str:
    parts = [f"- processo {p.get('protocolo','')}"]
    topic = (p.get("topic") or "").strip()
    if topic:
        parts.append(f"  tópico: {topic}")
    summary = (p.get("summary") or p.get("resumo") or "").strip()
    if summary:
        parts.append(f"  resumo: {summary[:400]}")
    if p.get("top_unidades"):
        parts.append(f"  unidades: {', '.join(p['top_unidades'])}")
    if p.get("top_tipos_acao"):
        parts.append(f"  ações: {', '.join(p['top_tipos_acao'])}")
    return "\n".join(parts)


def name_cluster(
    samples: list[dict],
    llm_call: Callable[[list[dict[str, str]]], str],
    *,
    sub_names: list[str] | None = None,
    profile: str | None = None,
    sibling_profiles: list[str] | None = None,
    top_keywords: list[tuple[str, int]] | None = None,
    distinctive_keywords: list[tuple[str, float]] | None = None,
) -> dict[str, Any]:
    user_msg = ""
    if top_keywords:
        kws = ", ".join(f"{k} ({c}x)" for k, c in top_keywords[:12])
        user_msg += (
            "Palavras-chave mais frequentes nos documentos iniciais desta categoria "
            f"(o TEMA geral, provavelmente partilhado com categorias vizinhas):\n{kws}\n\n"
        )
    if distinctive_keywords:
        dks = ", ".join(f"{k} ({lift}x mais provável aqui)" for k, lift in distinctive_keywords)
        user_msg += (
            "Palavras-chave DISTINTIVAS desta categoria — sobre-representadas aqui em relação "
            f"ao resto do corpus. Use-as para QUALIFICAR o tema:\n{dks}\n\n"
        )
    user_msg += (
        f"Amostra de {len(samples)} processos desta categoria:\n\n"
        + "\n\n".join(_format_sample(s) for s in samples)
    )
    if profile:
        user_msg += f"\n\nPerfil quantitativo deste subgrupo: {profile}."
    if sibling_profiles:
        others = "\n- ".join(sibling_profiles[:12])
        user_msg += (
            "\n\nEste grupo COEXISTE com outros grupos parecidos, cujos perfis são:\n- "
            + others
            + "\n\nDê um nome ESPECÍFICO que DISTINGA este grupo dos demais — destaque o que o "
            "diferencia: o FLUXO dominante, o CONTEÚDO/assunto específico, o porte/duração, ou o tipo. "
            "Não repita apenas o tema comum sem qualificá-lo."
        )
    if sub_names:
        uniq = list(dict.fromkeys(n for n in sub_names if n))
        if uniq:
            user_msg += (
                "\n\nEsta categoria AGRUPA as seguintes subcategorias:\n- "
                + "\n- ".join(uniq[:20])
                + "\n\nEscolha um nome que ENGLOBE todas essas subcategorias — capturando o "
                "assunto comum a elas, específico ao tema (não um rótulo administrativo vago)."
            )
    messages = [
        {"role": "system", "content": NAMING_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
    try:
        raw = llm_call(messages)
    except Exception as e:
        log.warning("LLM naming call failed: %s — using defensive default", e)
        return _default_name(samples)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("LLM naming returned invalid JSON: %s", raw[:200])
        return _default_name(samples)

    nome = (data.get("nome") or "").strip()
    descricao = (data.get("descricao") or "").strip()
    marcadores = data.get("marcadores") or []
    if not nome:
        return _default_name(samples)
    if not isinstance(marcadores, list):
        marcadores = []
    return {
        "nome": nome[:120],
        "descricao": descricao[:500],
        "marcadores": [str(m)[:80] for m in marcadores][:5],
    }


def _disambiguate_names(out: dict[str, dict[str, Any]], cids: list[str]) -> None:
    used: set[str] = set()
    for cid in cids:
        info = out.get(cid)
        if not info:
            continue
        base = (info.get("nome") or "").strip()
        cand = base
        if cand.lower() in used:
            suffix = next(
                (m.strip() for m in info.get("marcadores", [])
                 if m and m.strip().lower() not in base.lower()),
                None,
            )
            cand = f"{base} — {suffix}" if suffix else base
            if cand.lower() in used:
                i = 2
                while f"{cand} ({i})".lower() in used:
                    i += 1
                cand = f"{cand} ({i})"
        used.add(cand.lower())
        info["nome"] = cand[:120]


def _default_name(samples: list[dict]) -> dict[str, Any]:
    return {
        "nome": "Cluster sem nome",
        "descricao": f"Categoria emergente com {len(samples)} processos.",
        "marcadores": [],
    }


def name_all_clusters(
    catalog: ClusterCatalog,
    sample_loader: Callable[[list[str]], list[dict]],
    llm_call: Callable[[list[dict[str, str]]], str],
    *,
    samples_per_cluster: int = 5,
    workers: int = 1,
    profiles: dict[str, str] | None = None,
    macro_profiles: dict[str, str] | None = None,
    keywords_by_pf: dict[str, list[str]] | None = None,
    near_duplicate_threshold: float = 0.55,
) -> dict[str, dict[str, Any]]:
    from collections import Counter as _Counter

    _corpus_kw: _Counter = _Counter()
    for _kws in (keywords_by_pf or {}).values():
        _corpus_kw.update(_kws)
    _n_corpus = max(1, len(keywords_by_pf or {}))

    def _kw_counts(protos):
        c: _Counter = _Counter()
        for pf in protos:
            for kw in keywords_by_pf.get(pf) or []:
                c[kw] += 1
        return c

    def _top_kw(protos, limit=12):
        if not keywords_by_pf:
            return None
        return _kw_counts(protos).most_common(limit) or None

    def _distinct_kw(protos, limit=8):
        if not keywords_by_pf:
            return None
        c = _kw_counts(protos)
        return distinctive_keywords(c, _corpus_kw, n_cluster=max(1, len(protos)),
                                    n_corpus=_n_corpus, limit=limit) or None

    run_id = catalog.run_id
    out: dict[str, dict[str, Any]] = {}
    profiles = profiles or {}

    def _name_one(task: tuple[str, list[str], dict]) -> tuple[str, dict[str, Any]]:
        cid, protos, kwargs = task
        try:
            samples = sample_loader(protos)
        except Exception as e:
            log.warning("sample load failed for %s: %s", cid, e)
            samples = []
        return cid, name_cluster(samples, llm_call, **kwargs)

    def _run(tasks: list[tuple]) -> None:
        if workers <= 1:
            for t in tasks:
                cid, name = _name_one(t)
                out[cid] = name
        else:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(_name_one, t) for t in tasks]
                for fut in as_completed(futs):
                    cid, name = fut.result()
                    out[cid] = name

    micro_cids_by_macro: dict[int, list[str]] = defaultdict(list)
    micro_cid_of: dict[int, list[tuple[str, list[str]]]] = defaultdict(list)
    for desc in catalog.micro_clusters:
        cid = _category_id(run_id, desc.nivel, desc.micro_label, desc.macro_label)
        micro_cids_by_macro[desc.macro_label].append(cid)
        micro_cid_of[desc.macro_label].append((cid, desc.member_protocolos[:samples_per_cluster]))
    micro_tasks = []
    for _macro_label, items in micro_cid_of.items():
        sibling_cids = [c for c, _ in items]
        for cid, protos in items:
            sibs = [profiles[c] for c in sibling_cids if c != cid and c in profiles]
            micro_tasks.append((cid, protos, {
                "profile": profiles.get(cid),
                "sibling_profiles": sibs or None,
                "top_keywords": _top_kw(protos),
                "distinctive_keywords": _distinct_kw(protos),
            }))
    _run(micro_tasks)
    for cids in micro_cids_by_macro.values():
        _disambiguate_names(out, cids)

    macro_cids: list[str] = []
    macro_kw: dict[str, list[str]] = {}
    macro_protos: dict[str, list[str]] = {}
    macro_tasks = []
    for desc in catalog.macro_clusters:
        cid = _category_id(run_id, "macro", desc.macro_label)
        macro_cids.append(cid)
        protos = desc.member_protocolos[:samples_per_cluster]
        macro_protos[cid] = protos
        sub = [out[c]["nome"] for c in micro_cids_by_macro.get(desc.macro_label, []) if c in out]
        macro_kw[cid] = desc.member_protocolos
        macro_tasks.append((cid, protos, {
            "sub_names": sub or None,
            "top_keywords": _top_kw(desc.member_protocolos),
            "distinctive_keywords": _distinct_kw(desc.member_protocolos)}))
    _run(macro_tasks)

    macro_names = {cid: (out.get(cid, {}).get("nome") or "") for cid in macro_cids}
    dup_groups = near_duplicate_groups(macro_names, threshold=near_duplicate_threshold)
    if dup_groups:
        log.info("naming pass 2: %d group(s) of near-identical names, %d categories renamed "
                 "with their rivals in view", len(dup_groups), sum(len(g) for g in dup_groups))
        rename_tasks = []
        for cids in dup_groups:
            for cid in cids:
                sibs = []
                for other in cids:
                    if other == cid:
                        continue
                    dk = ", ".join(k for k, _ in (_distinct_kw(macro_kw.get(other, [])) or [])[:5])
                    label = macro_names.get(other, "")
                    if macro_profiles and other in macro_profiles:
                        label = f"{label} — {macro_profiles[other]}"
                    sibs.append(label + (f" [distintivo: {dk}]" if dk else ""))
                rename_tasks.append((cid, macro_protos.get(cid, []), {
                    "profile": (macro_profiles or {}).get(cid),
                    "sibling_profiles": sibs or None,
                    "top_keywords": _top_kw(macro_kw.get(cid, [])),
                    "distinctive_keywords": _distinct_kw(macro_kw.get(cid, [])),
                }))
        if rename_tasks:
            _run(rename_tasks)

    _disambiguate_names(out, macro_cids)
    return out


_NAME_STOPWORDS = frozenset({
    "de", "do", "da", "dos", "das", "e", "para", "em", "a", "o", "as", "os", "no", "na",
    "por", "com", "processos", "processo", "solicitacao", "solicitação",
})


def _name_tokens(name: str) -> set[str]:
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", (name or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {t for t in re.findall(r"\w+", s) if t not in _NAME_STOPWORDS and len(t) > 2}


def distinctive_keywords(cluster_counts, corpus_counts, *, n_cluster, n_corpus, limit=8,
                         alpha=0.5):
    out = []
    for kw, c in cluster_counts.items():
        p_in = (c + alpha) / (n_cluster + 2 * alpha)
        rest = max(0, corpus_counts.get(kw, 0) - c)
        p_out = (rest + alpha) / (max(1, n_corpus - n_cluster) + 2 * alpha)
        if p_in <= p_out:
            continue
        out.append((kw, round(p_in / p_out, 2), c))
    out.sort(key=lambda r: (-r[1], -r[2]))
    return [(kw, lift) for kw, lift, _ in out[:limit]]


def near_duplicate_groups(names: dict[str, str], *, threshold: float = 0.6) -> list[list[str]]:
    import itertools
    toks = {cid: _name_tokens(n) for cid, n in names.items() if n}
    adj: dict[str, set[str]] = {cid: set() for cid in toks}
    for (a, ta), (b, tb) in itertools.combinations(toks.items(), 2):
        if not ta or not tb:
            continue
        if len(ta & tb) / len(ta | tb) >= threshold:
            adj[a].add(b)
            adj[b].add(a)
    seen: set[str] = set()
    groups: list[list[str]] = []
    for cid in toks:
        if cid in seen or not adj[cid]:
            continue
        stack, comp = [cid], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(adj[x] - seen)
        if len(comp) > 1:
            groups.append(sorted(comp))
    return groups
