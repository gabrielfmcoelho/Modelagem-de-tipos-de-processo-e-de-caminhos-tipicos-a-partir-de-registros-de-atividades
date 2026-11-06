from __future__ import annotations

import pytest

from ..core.config import ConfigError, Settings


def test_overlay_ignores_none_values() -> None:
    s = Settings(neo4j_uri="bolt://a", neo4j_password="pw")
    s2 = s.overlay(neo4j_uri=None, neo4j_user="other")
    assert s2.neo4j_uri == "bolt://a"
    assert s2.neo4j_user == "other"
    assert s2.neo4j_password == "pw"


def test_overlay_puts_unknown_keys_in_extra() -> None:
    s = Settings().overlay(custom_flag="yes")
    assert s.extra.get("custom_flag") == "yes"


def test_require_neo4j_without_password_raises() -> None:
    s = Settings()
    with pytest.raises(ConfigError, match="NEO4J_PASSWORD"):
        s.require_neo4j()


def test_require_neo4j_with_password_passes() -> None:
    Settings(neo4j_password="pw").require_neo4j()


def test_require_trino_missing_fields_raises() -> None:
    s = Settings(trino_host="h", trino_user="u")
    with pytest.raises(ConfigError, match="TRINO_PASSWORD"):
        s.require_trino()


def test_require_trino_all_fields_passes() -> None:
    Settings(trino_host="h", trino_user="u", trino_password="p").require_trino()


def test_from_env_resolves_new_fields_with_defaults(monkeypatch) -> None:
    for name in (
        "PIPELINE_DEVICE", "PIPELINE_DTYPE", "PIPELINE_EMBED_BATCH_SIZE",
        "OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_MODEL_EMBEDDING",
        "OPENAI_MODEL_NER", "OPENAI_MODEL_TEXTO", "OPENAI_MODEL_VISAO",
        "OPENAI_MODEL_EVALUATE", "OPENAI_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    s = Settings.from_env()
    assert s.pipeline_device == "auto"
    assert s.pipeline_dtype == "bf16"
    assert s.pipeline_embed_batch_size == 64
    assert s.openai_base_url == "https://new-plataforma.sobdemanda.mandu.piaui.pro/v1"
    assert s.openai_api_key == ""
    assert s.openai_model is None
    assert s.openai_model_embedding is None
    assert s.openai_model_ner is None
    assert s.openai_model_texto is None
    assert s.openai_model_visao is None
    assert s.openai_model_evaluate is None
    assert s.openai_timeout == 120


def test_from_env_resolves_new_fields_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_DEVICE", "cuda")
    monkeypatch.setenv("PIPELINE_DTYPE", "fp16")
    monkeypatch.setenv("PIPELINE_EMBED_BATCH_SIZE", "128")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://x/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("OPENAI_MODEL_NER", "ner-model")
    monkeypatch.setenv("OPENAI_TIMEOUT", "30")
    s = Settings.from_env()
    assert s.pipeline_device == "cuda"
    assert s.pipeline_dtype == "fp16"
    assert s.pipeline_embed_batch_size == 128
    assert s.openai_base_url == "http://x/v1"
    assert s.openai_api_key == "k"
    assert s.openai_model_ner == "ner-model"
    assert s.openai_timeout == 30
