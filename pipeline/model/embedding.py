
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx
from openai import OpenAI

from ..core.config import Settings

log = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
DEFAULT_EMBEDDING_DIMENSION = 1024


class Embedder(Protocol):
    model_name: str
    dimension: int

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class MandoEmbedderConfig:
    base_url: str
    api_key: str
    model: str = DEFAULT_EMBEDDING_MODEL
    timeout_s: int = 60
    max_chars: int = 8000


class MandoEmbedder:
    def __init__(self, config: MandoEmbedderConfig) -> None:
        self.config = config
        self.model_name = config.model
        self.dimension: int = 0
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "EMPTY",
            timeout=httpx.Timeout(float(config.timeout_s), connect=10.0),
        )

    def probe(self) -> int:
        resp = self._client.embeddings.create(model=self.model_name, input="probe")
        emb = resp.data[0].embedding
        self.dimension = len(emb)
        return self.dimension

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        truncated = [(t or "")[: self.config.max_chars] for t in texts]
        resp = self._client.embeddings.create(
            model=self.model_name, input=truncated,
        )
        out = [d.embedding for d in resp.data]
        if out and self.dimension == 0:
            self.dimension = len(out[0])
        return out


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None
        self._device: str = "cpu"
        self.dimension: int = 0

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers not installed. Run: "
                "`pip install sentence-transformers`."
            ) from e
        from ..core.devices import select_device

        self._device = select_device()
        log.info(
            "Loading local embedding model: %s on %s (this may take a minute)",
            self.model_name, self._device,
        )
        self._model = SentenceTransformer(self.model_name, device=self._device)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def probe(self) -> int:
        self._load()
        return self.dimension

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if not texts:
            return []
        from ..core.devices import autocast_for

        settings = Settings.from_env()
        batch_size = settings.pipeline_embed_batch_size
        with autocast_for(self._device, settings=settings):
            arr = self._model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return arr.tolist()


EmbedderPreference = Literal["auto", "mandu", "local"]


def build_embedder(
    settings: Settings | None = None,
    *,
    preference: EmbedderPreference = "auto",
    model: str | None = None,
) -> Embedder:
    settings = settings or Settings.from_env()
    chosen_model = model or settings.openai_model_embedding or DEFAULT_EMBEDDING_MODEL

    def _build_mandu() -> MandoEmbedder:
        cfg = MandoEmbedderConfig(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=chosen_model,
        )
        emb = MandoEmbedder(cfg)
        emb.probe()
        log.info("Embedder: Mandu /v1/embeddings (model=%s, dim=%d)", emb.model_name, emb.dimension)
        return emb

    def _build_local() -> SentenceTransformerEmbedder:
        emb = SentenceTransformerEmbedder(chosen_model)
        emb.probe()
        log.info("Embedder: local sentence-transformers (model=%s, dim=%d)", emb.model_name, emb.dimension)
        return emb

    if preference == "mandu":
        return _build_mandu()
    if preference == "local":
        return _build_local()

    try:
        return _build_mandu()
    except Exception as e:
        log.warning("Mandu embeddings unavailable (%s) — falling back to local model.", e)
        return _build_local()
