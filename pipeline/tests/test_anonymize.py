from __future__ import annotations

import subprocess
import sys

from ..model.anonymize import Entity, anonymize_text, cnpj_valid, cpf_valid, ner_entities, placeholder, regex_entities

VALID_CPF = "529.982.247-25"
VALID_CPF_BARE = "52998224725"
VALID_CNPJ = "11.222.333/0001-81"
VALID_CNPJ_BARE = "11222333000181"


def test_cpf_checksum_accepts_valid():
    assert cpf_valid("52998224725") is True
    assert cpf_valid("01806704331") is True


def test_cpf_checksum_rejects_invalid():
    assert cpf_valid("12345678901") is False
    assert cpf_valid("11111111111") is False
    assert cpf_valid("52998224726") is False
    assert cpf_valid("5299822472") is False


def test_cnpj_checksum():
    assert cnpj_valid("11222333000181") is True
    assert cnpj_valid("11222333000182") is False
    assert cnpj_valid("00000000000000") is False


def test_regex_entities_cpf_formatted_and_bare():
    text = f"CPF: {VALID_CPF} e também {VALID_CPF_BARE} no texto"
    ents = regex_entities(text)
    cpfs = [e for e in ents if e.label == "CPF"]
    assert {e.text for e in cpfs} == {VALID_CPF, VALID_CPF_BARE}


def test_regex_entities_rejects_random_digit_runs():
    text = "protocolo 12345678901 e conta 98765432100123"
    assert regex_entities(text) == []


def test_regex_entities_cnpj():
    text = f"CNPJ {VALID_CNPJ} ou {VALID_CNPJ_BARE}"
    ents = regex_entities(text)
    assert {e.text for e in ents if e.label == "CNPJ"} == {VALID_CNPJ, VALID_CNPJ_BARE}


def test_regex_entities_email_and_matricula():
    text = "E-MAIL: daniele.reis@sead.pi.gov.br MATRÍCULA: 401285-2 fim"
    ents = {e.label: e.text for e in regex_entities(text)}
    assert ents["EMAIL"] == "daniele.reis@sead.pi.gov.br"
    assert ents["MATRICULA"] == "401285-2"


def test_regex_entities_matricula_needs_context():
    assert regex_entities("valor 401285-2 sem contexto") == []


def test_placeholder_deterministic_and_typed():
    a = placeholder("PESSOA", "João Silva")
    b = placeholder("PESSOA", "João Silva")
    assert a == b
    assert a.startswith("<PESSOA_") and a.endswith(">") and len(a) == len("<PESSOA_>") + 8


def test_placeholder_normalizes_case_and_accents():
    assert placeholder("PESSOA", "João Silva") == placeholder("PESSOA", "JOAO  SILVA")


def test_placeholder_digit_labels_normalize_format():
    assert placeholder("CPF", VALID_CPF) == placeholder("CPF", VALID_CPF_BARE)


def test_placeholder_differs_by_label_and_entity():
    assert placeholder("PESSOA", "x y z") != placeholder("EMPRESA", "x y z")
    assert placeholder("PESSOA", "Maria Souza") != placeholder("PESSOA", "Ana Souza")


def test_placeholder_stable_across_processes():
    expected = placeholder("PESSOA", "João Silva")
    code = "from pipeline.model.anonymize import placeholder; print(placeholder('PESSOA', 'João Silva'))"
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert out == expected


def test_anonymize_text_replaces_with_word_boundaries():
    text = f"O CPF {VALID_CPF} pertence a Maria de Souza Lima."
    ents = regex_entities(text) + [Entity("PESSOA", "Maria de Souza Lima", "Maria de Souza Lima")]
    out, stats = anonymize_text(text, ents)
    assert VALID_CPF not in out
    assert "Maria de Souza Lima" not in out
    assert stats.total == 2
    assert stats.replacements == {"CPF": 1, "PESSOA": 1}


def test_anonymize_text_longest_span_wins_on_nested():
    text = "Assinado por Maria de Souza Lima hoje."
    ents = [
        Entity("PESSOA", "Souza Lima", "Souza Lima"),
        Entity("PESSOA", "Maria de Souza Lima", "Maria de Souza Lima"),
    ]
    out, stats = anonymize_text(text, ents)
    assert out == f"Assinado por {placeholder('PESSOA', 'Maria de Souza Lima')} hoje."
    assert stats.total == 1


def test_anonymize_text_overlapping_spans_no_corruption():
    text = "João Silva Santos compareceu."
    ents = [
        Entity("PESSOA", "João Silva", "João Silva"),
        Entity("PESSOA", "Silva Santos", "Silva Santos"),
    ]
    out, stats = anonymize_text(text, ents)
    assert stats.total == 1
    assert "Silva" not in out.replace("Santos", "") or "João" not in out


def test_anonymize_text_case_insensitive_match():
    text = "MARIA DE SOUZA e Maria de Souza"
    ents = [Entity("PESSOA", "Maria de Souza", "Maria de Souza")]
    out, stats = anonymize_text(text, ents)
    token = placeholder("PESSOA", "Maria de Souza")
    assert out == f"{token} e {token}"
    assert stats.total == 2


def test_anonymize_text_word_boundary_prevents_partial():
    text = "Silvano não é Silva."
    ents = [Entity("PESSOA", "Silva", "Silva")]
    out, _ = anonymize_text(text, ents)
    assert out.startswith("Silvano")
    assert "Silva." not in out


def test_anonymize_text_deterministic():
    text = f"CPF {VALID_CPF} de Ana Lima, email ana@x.gov.br"
    ents = regex_entities(text) + [Entity("PESSOA", "Ana Lima", "Ana Lima")]
    out1, _ = anonymize_text(text, ents)
    out2, _ = anonymize_text(text, list(reversed(ents)))
    assert out1 == out2


def test_anonymize_text_idempotent():
    text = f"CPF {VALID_CPF} de Ana Lima"
    ents = regex_entities(text) + [Entity("PESSOA", "Ana Lima", "Ana Lima")]
    once, _ = anonymize_text(text, ents)
    twice, stats = anonymize_text(once, ents)
    assert twice == once
    assert stats.total == 0
    assert regex_entities(once) == []


def test_ner_entities_maps_keys_and_filters_absent_spans():
    text = "Contrato com ACME LTDA assinado por Ana Beatriz Costa."
    payload = {
        "entities": {
            "pessoa": [{"text": "Ana Beatriz Costa", "canonical": "Ana Beatriz Costa", "provenance": "hybrid"}],
            "pessoa_juridica": [{"text": "ACME LTDA", "canonical": "ACME Ltda", "provenance": "gliner"}],
            "orgao": [{"text": "SEAD-PI", "canonical": "SEAD-PI", "provenance": "gliner"}],
            "email": [{"text": "naoexiste@x.com", "canonical": "naoexiste@x.com", "provenance": "llm"}],
        },
    }
    ents = ner_entities(text, payload)
    assert {(e.label, e.text) for e in ents} == {
        ("PESSOA", "Ana Beatriz Costa"),
        ("EMPRESA", "ACME LTDA"),
    }


def test_ner_entities_accepts_bare_strings_and_missing_payload():
    assert ner_entities("qualquer", None) == []
    ents = ner_entities("fulano citou Beltrano da Silva", {"entities": {"pessoa": ["Beltrano da Silva"]}})
    assert ents == [Entity("PESSOA", "Beltrano da Silva", "Beltrano da Silva")]


def test_ner_canonical_drives_placeholder_identity():
    e1 = Entity("PESSOA", "M. Souza", "Maria Souza")
    e2 = Entity("PESSOA", "MARIA SOUZA", "Maria Souza")
    out, _ = anonymize_text("M. Souza e MARIA SOUZA", [e1, e2])
    token = placeholder("PESSOA", "Maria Souza")
    assert out == f"{token} e {token}"


def test_ner_entities_maps_llm_alias_keys():
    text = "Maria Souza, RG 1.234.567 SSP-PI, representa a TechCorp."
    payload = {
        "entities": {
            "pessoa_fisica": ["Maria Souza"],
            "rg": ["1.234.567 SSP-PI"],
            "empresa": ["TechCorp"],
        },
    }
    ents = ner_entities(text, payload)
    assert {(e.label, e.text) for e in ents} == {
        ("PESSOA", "Maria Souza"),
        ("DOCUMENTO", "1.234.567 SSP-PI"),
        ("EMPRESA", "TechCorp"),
    }


def test_anonymize_text_replaces_spans_glued_to_word_chars():
    from ..model.anonymize import Entity

    text = "CPF Nº943.361.563-87 e E-Mail: fulano@gmail.com_______ fim"
    entities = [
        Entity(label="CPF", text="943.361.563-87", canonical="943.361.563-87"),
        Entity(label="EMAIL", text="fulano@gmail.com", canonical="fulano@gmail.com"),
    ]
    anon, stats = anonymize_text(text, entities)
    assert "943.361.563-87" not in anon
    assert "fulano@gmail.com" not in anon
    assert stats.total == 2
    assert regex_entities(anon) == []
