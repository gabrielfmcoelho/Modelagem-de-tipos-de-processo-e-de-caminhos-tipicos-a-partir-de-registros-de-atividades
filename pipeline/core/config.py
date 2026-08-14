
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    def _load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


class ConfigError(RuntimeError):
    pass


_LOADED_DOTENV = False


def _ensure_dotenv_loaded() -> None:
    global _LOADED_DOTENV
    if _LOADED_DOTENV:
        return
    _LOADED_DOTENV = True
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if candidate.is_file():
            _load_dotenv(candidate, override=False)
            return


def _env(name: str, default: Any = None, *, cast: type | None = None) -> Any:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    if cast is int:
        return int(raw)
    if cast is float:
        return float(raw)
    if cast is bool:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return raw


@dataclass
class Settings:
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str | None = None
    neo4j_database: str | None = None

    trino_host: str | None = None
    trino_port: int = 8443
    trino_user: str | None = None
    trino_password: str | None = None
    trino_catalog: str = "iceberg"
    trino_schema: str = "sei_bronze"
    trino_http_scheme: str = "https"
    trino_verify_ssl: bool = False

    sei_base_url: str | None = None
    sei_api_user: str | None = None
    sei_api_password: str | None = None
    sei_token: str | None = None

    batch_size: int = 1000
    workers: int = 8
    emit_json_dir: Path | None = None
    read_json_dir: Path | None = None
    log_level: str = "INFO"

    pipeline_device: str = "auto"
    pipeline_dtype: str = "bf16"
    pipeline_embed_batch_size: int = 64

    openai_base_url: str = "https://api.sobdemanda.mandu.piaui.pro/v1"
    openai_api_key: str = ""
    openai_model: str | None = None
    openai_model_embedding: str | None = None
    openai_model_ner: str | None = None
    openai_model_texto: str | None = None
    openai_model_visao: str | None = None
    openai_model_evaluate: str | None = None
    openai_timeout: int = 120

    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.openai_base_url:
            base = self.openai_base_url.rstrip("/")
            self.openai_base_url = base if base.endswith("/v1") else base + "/v1"


    @classmethod
    def from_env(cls) -> Settings:
        _ensure_dotenv_loaded()
        return cls(
            neo4j_uri=_env("NEO4J_URI", cls.neo4j_uri),
            neo4j_user=_env("NEO4J_USER", cls.neo4j_user),
            neo4j_password=_env("NEO4J_PASSWORD"),
            neo4j_database=_env("NEO4J_DATABASE"),
            trino_host=_env("TRINO_HOST"),
            trino_port=_env("TRINO_PORT", cls.trino_port, cast=int),
            trino_user=_env("TRINO_USER"),
            trino_password=_env("TRINO_PASSWORD"),
            trino_catalog=_env("TRINO_CATALOG", cls.trino_catalog),
            trino_schema=_env("TRINO_SCHEMA", cls.trino_schema),
            trino_http_scheme=_env("TRINO_HTTP_SCHEME", cls.trino_http_scheme),
            trino_verify_ssl=_env("TRINO_VERIFY_SSL", cls.trino_verify_ssl, cast=bool),
            sei_base_url=_env("SEI_BASE_URL"),
            sei_api_user=_env("SEI_API_USER"),
            sei_api_password=_env("SEI_API_PASSWORD"),
            sei_token=_env("SEI_TOKEN"),
            batch_size=_env("PIPELINE_BATCH_SIZE", cls.batch_size, cast=int),
            workers=_env("PIPELINE_WORKERS", cls.workers, cast=int),
            log_level=_env("LOG_LEVEL", cls.log_level),
            pipeline_device=_env("PIPELINE_DEVICE", cls.pipeline_device),
            pipeline_dtype=_env("PIPELINE_DTYPE", cls.pipeline_dtype),
            pipeline_embed_batch_size=_env(
                "PIPELINE_EMBED_BATCH_SIZE", cls.pipeline_embed_batch_size, cast=int),
            openai_base_url=_env("OPENAI_BASE_URL", cls.openai_base_url),
            openai_api_key=_env("OPENAI_API_KEY", cls.openai_api_key),
            openai_model=_env("OPENAI_MODEL"),
            openai_model_embedding=_env("OPENAI_MODEL_EMBEDDING"),
            openai_model_ner=_env("OPENAI_MODEL_NER"),
            openai_model_texto=_env("OPENAI_MODEL_TEXTO"),
            openai_model_visao=_env("OPENAI_MODEL_VISAO"),
            openai_model_evaluate=_env("OPENAI_MODEL_EVALUATE"),
            openai_timeout=_env("OPENAI_TIMEOUT", cls.openai_timeout, cast=int),
        )

    def overlay(self, **overrides: Any) -> Settings:
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        for key, value in overrides.items():
            if value is None:
                continue
            if key not in data:
                data["extra"] = {**data.get("extra", {}), key: value}
                continue
            data[key] = value
        return Settings(**data)


    def require_neo4j(self) -> None:
        if not self.neo4j_password:
            raise ConfigError(
                "NEO4J_PASSWORD is not set. Provide it via env var, .env, "
                "or --neo4j-password."
            )

    def require_trino(self) -> None:
        missing = [
            name for name in ("trino_host", "trino_user", "trino_password")
            if not getattr(self, name)
        ]
        if missing:
            raise ConfigError(
                "Missing Trino settings: "
                + ", ".join(m.upper() for m in missing)
                + ". Provide them via TRINO_* env vars or .env."
            )

