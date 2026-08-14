
from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .classifier import TASK_GROUPS

log = logging.getLogger(__name__)


ALGO_VERSION = "2.0"


def _tipo_acao_vocab() -> list[str]:
    out: list[str] = []
    for group_key in sorted(TASK_GROUPS.keys()):
        for task in sorted(TASK_GROUPS[group_key]["tasks"]):
            out.append(task)
    out.append("OUTROS")
    return out


TIPO_ACAO_VOCAB = _tipo_acao_vocab()
TIPO_ACAO_DIM = len(TIPO_ACAO_VOCAB)
_TIPO_ACAO_INDEX = {t: i for i, t in enumerate(TIPO_ACAO_VOCAB)}


@dataclass
class ProcessoInput:

    protocolo_formatado: str
    documentos: list[dict]
    unidades_visitadas: list[str]
    unidades_cronologicas: list[str]
    atividades_tipo_acao: list[str]
    first_doc_topic_embedding: list[float] | None = None
    keywords: list[str] | None = None


@dataclass
class FeatureWeights:
    first_doc_weight: float = 3.0
    early_doc_weight: float = 1.5
    early_doc_until_rank: int = 3
    default_doc_weight: float = 1.0


@dataclass
class BlockWeights:
    semantic: float = 1.0
    topic: float = 1.0
    unigram: float = 1.0
    bigram: float = 1.0
    tipo_acao: float = 1.0
    keyword: float = 1.0


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _l2_normalize_rows(m: np.ndarray) -> np.ndarray:
    if m.size == 0:
        return m.astype(np.float32)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype(np.float32)


def _stack_blocks(blocks: list[np.ndarray], n_rows: int) -> np.ndarray:
    dim = 0
    for v in blocks:
        if v.size > 0:
            dim = v.shape[0]
            break
    if dim == 0:
        return np.zeros((n_rows, 0), dtype=np.float32)
    return np.stack([
        v if v.size == dim else np.zeros(dim, dtype=np.float32)
        for v in blocks
    ]).astype(np.float32)


def _doc_weight(rank_one_based: int, w: FeatureWeights) -> float:
    if rank_one_based == 1:
        return w.first_doc_weight
    if rank_one_based <= w.early_doc_until_rank:
        return w.early_doc_weight
    return w.default_doc_weight


def _dedup_consecutive(seq: list[str]) -> list[str]:
    out: list[str] = []
    for x in seq:
        if not x:
            continue
        if not out or out[-1] != x:
            out.append(x)
    return out


def _bigram_tokens(seq_dedup: list[str]) -> list[str]:
    return [f"{a}__{b}" for a, b in zip(seq_dedup[:-1], seq_dedup[1:])]


def semantic_embedding(processo: ProcessoInput, weights: FeatureWeights | None = None,
                       *, first_doc_only: bool = True) -> np.ndarray:
    weights = weights or FeatureWeights()
    docs = [d for d in processo.documentos if d.get("embedding")]
    if not docs:
        return np.zeros(0, dtype=np.float32)

    if first_doc_only:
        emb = np.asarray(docs[0]["embedding"], dtype=np.float64)
        return _l2_normalize(emb).astype(np.float32)

    dim = len(docs[0]["embedding"])
    acc = np.zeros(dim, dtype=np.float64)
    total_w = 0.0
    for rank, d in enumerate(docs, start=1):
        emb = np.asarray(d["embedding"], dtype=np.float64)
        if emb.shape != (dim,):
            log.warning(
                "doc %s embedding dim mismatch (%d vs %d) — skipping",
                d.get("numero"), emb.shape[0] if emb.size else 0, dim,
            )
            continue
        w = _doc_weight(rank, weights)
        acc += w * emb
        total_w += w
    if total_w == 0.0:
        return np.zeros(dim, dtype=np.float32)
    return _l2_normalize(acc / total_w).astype(np.float32)


def topic_embedding(processo: ProcessoInput) -> np.ndarray:
    v = processo.first_doc_topic_embedding
    if not v:
        return np.zeros(0, dtype=np.float32)
    return _l2_normalize(np.asarray(v, dtype=np.float64)).astype(np.float32)


def apply_cutoff(events: list[dict], atividades: list[dict], frac: float):
    if frac >= 1.0:
        return events, atividades
    stamps = sorted(s for s in
                    [e.get("ts") or "" for e in events] + [a.get("ts") or "" for a in atividades]
                    if s)
    if not stamps:
        return events, atividades
    idx = max(0, min(len(stamps) - 1, int(len(stamps) * frac) - 1))
    cut = stamps[idx]
    return ([e for e in events if (e.get("ts") or "") <= cut],
            [a for a in atividades if (a.get("ts") or "") <= cut])


def tipo_acao_histogram(processo: ProcessoInput) -> np.ndarray:
    hist = np.zeros(TIPO_ACAO_DIM, dtype=np.float32)
    n = 0
    for tipo in processo.atividades_tipo_acao:
        idx = _TIPO_ACAO_INDEX.get(tipo, _TIPO_ACAO_INDEX["OUTROS"])
        hist[idx] += 1
        n += 1
    if n > 0:
        hist /= n
    return hist


def keyword_text(processo: ProcessoInput) -> str:
    return " ".join((k or "").replace(" ", "_") for k in (processo.keywords or []) if k)


def unidade_unigram_text(processo: ProcessoInput) -> str:
    return " ".join(sorted(set(processo.unidades_visitadas)))


def unidade_bigram_text(processo: ProcessoInput) -> str:
    seq = _dedup_consecutive(list(processo.unidades_cronologicas))
    if len(seq) < 2:
        return ""
    return " ".join(_bigram_tokens(seq))


def feature_hash(processo: ProcessoInput, weights: FeatureWeights | None = None,
                 algo_version: str = ALGO_VERSION, *,
                 first_doc_only: bool = True,
                 block_weights: BlockWeights | None = None,
                 cutoff_frac: float = 1.0) -> str:
    weights = weights or FeatureWeights()
    block_weights = block_weights or BlockWeights()
    h = hashlib.sha256()
    h.update(algo_version.encode())
    h.update(b"|")
    h.update(repr((
        weights.first_doc_weight,
        weights.early_doc_weight,
        weights.early_doc_until_rank,
        weights.default_doc_weight,
        first_doc_only,
        block_weights.semantic,
        block_weights.topic,
        block_weights.unigram,
        block_weights.bigram,
        block_weights.tipo_acao,
    )).encode())
    if processo.keywords:
        h.update(b"|kw:")
        h.update(repr(sorted(processo.keywords)).encode())
    if block_weights.keyword != BlockWeights.keyword:
        h.update(b"|kwb:")
        h.update(repr(float(block_weights.keyword)).encode())
    if cutoff_frac < 1.0:
        h.update(b"|cut:")
        h.update(repr(float(cutoff_frac)).encode())
    h.update(b"|")
    for d in processo.documentos:
        h.update((d.get("embedding_hash") or d.get("numero") or "").encode())
        h.update(b"\x01")
    h.update(b"|")
    _emb_docs = [d for d in processo.documentos if d.get("embedding")]
    if _emb_docs:
        _first = _emb_docs[0]
        h.update(((_first.get("topic") or "") + "\x00" + (_first.get("summary") or "")).encode())
    h.update(b"|")
    for u in sorted(set(processo.unidades_visitadas)):
        h.update(u.encode())
        h.update(b"\x02")
    h.update(b"|")
    seq = _dedup_consecutive(list(processo.unidades_cronologicas))
    for u in seq:
        h.update(u.encode())
        h.update(b"\x03")
    h.update(b"|")
    counts: dict[str, int] = {}
    for t in processo.atividades_tipo_acao:
        counts[t] = counts.get(t, 0) + 1
    for k in sorted(counts.keys()):
        h.update(f"{k}={counts[k]}".encode())
        h.update(b"\x04")
    return h.hexdigest()


@dataclass
class BatchFeatures:
    protocolos: list[str]
    raw: np.ndarray
    semantic_dim: int
    unigram_dim: int
    bigram_dim: int
    tipo_acao_dim: int
    topic_dim: int = 0
    keyword_dim: int = 0
    keyword_vocab: list[str] | None = None
    unigram_vocab: list[str] = field(default_factory=list)
    bigram_vocab: list[str] = field(default_factory=list)


def build_batch_features(
    processos: Sequence[ProcessoInput],
    *,
    weights: FeatureWeights | None = None,
    block_weights: BlockWeights | None = None,
    first_doc_only: bool = True,
    unigram_max_features: int = 500,
    bigram_max_features: int = 1000,
    keyword_max_features: int = 1500,
    keyword_min_df: int = 3,
) -> BatchFeatures:
    from sklearn.feature_extraction.text import TfidfVectorizer

    weights = weights or FeatureWeights()
    block_weights = block_weights or BlockWeights()
    n = len(processos)

    sem_matrix = _stack_blocks(
        [semantic_embedding(p, weights, first_doc_only=first_doc_only) for p in processos], n)

    topic_matrix = _stack_blocks([topic_embedding(p) for p in processos], n)

    unigram_texts = [unidade_unigram_text(p) for p in processos]
    if any(unigram_texts):
        v_uni = TfidfVectorizer(
            analyzer="word", token_pattern=r"\S+",
            binary=True, max_features=unigram_max_features, sublinear_tf=False,
        )
        uni_sparse = v_uni.fit_transform(unigram_texts)
        uni_dense = uni_sparse.toarray().astype(np.float32)
        uni_vocab = sorted(v_uni.vocabulary_, key=lambda k: v_uni.vocabulary_[k])
    else:
        uni_dense = np.zeros((len(processos), 0), dtype=np.float32)
        uni_vocab = []

    bigram_texts = [unidade_bigram_text(p) for p in processos]
    if any(bigram_texts):
        v_bi = TfidfVectorizer(
            analyzer="word", token_pattern=r"\S+",
            binary=False, max_features=bigram_max_features, sublinear_tf=False,
        )
        bi_sparse = v_bi.fit_transform(bigram_texts)
        bi_dense = bi_sparse.toarray().astype(np.float32)
        bi_vocab = sorted(v_bi.vocabulary_, key=lambda k: v_bi.vocabulary_[k])
    else:
        bi_dense = np.zeros((len(processos), 0), dtype=np.float32)
        bi_vocab = []

    kw_texts = [keyword_text(p) for p in processos]
    if any(kw_texts):
        v_kw = TfidfVectorizer(
            analyzer="word", token_pattern=r"\S+", binary=True,
            max_features=keyword_max_features, min_df=min(keyword_min_df, max(1, n)),
            sublinear_tf=False,
        )
        try:
            kw_dense = v_kw.fit_transform(kw_texts).toarray().astype(np.float32)
            kw_vocab = sorted(v_kw.vocabulary_, key=lambda k: v_kw.vocabulary_[k])
        except ValueError:
            kw_dense = np.zeros((n, 0), dtype=np.float32)
            kw_vocab = []
    else:
        kw_dense = np.zeros((n, 0), dtype=np.float32)
        kw_vocab = []
    kw_dense = _l2_normalize_rows(kw_dense)

    hist_matrix = (np.stack([tipo_acao_histogram(p) for p in processos])
                   if n else np.zeros((0, TIPO_ACAO_DIM), dtype=np.float32))
    hist_matrix = _l2_normalize_rows(hist_matrix)

    sem_matrix = sem_matrix * block_weights.semantic
    topic_matrix = topic_matrix * block_weights.topic
    uni_dense = uni_dense * block_weights.unigram
    bi_dense = bi_dense * block_weights.bigram
    hist_matrix = hist_matrix * block_weights.tipo_acao
    kw_dense = kw_dense * block_weights.keyword

    raw = np.concatenate(
        [sem_matrix, topic_matrix, uni_dense, bi_dense, hist_matrix, kw_dense], axis=1
    ).astype(np.float32)

    return BatchFeatures(
        protocolos=[p.protocolo_formatado for p in processos],
        raw=raw,
        semantic_dim=sem_matrix.shape[1],
        topic_dim=topic_matrix.shape[1],
        unigram_dim=uni_dense.shape[1],
        bigram_dim=bi_dense.shape[1],
        tipo_acao_dim=hist_matrix.shape[1],
        unigram_vocab=uni_vocab,
        bigram_vocab=bi_vocab,
        keyword_dim=kw_dense.shape[1],
        keyword_vocab=kw_vocab,
    )


def reduce_with_umap(
    batch: BatchFeatures,
    *,
    n_components: int = 50,
    metric: str = "cosine",
    n_neighbors: int = 15,
    random_state: int = 42,
) -> np.ndarray:
    import umap

    n_samples = batch.raw.shape[0]
    if n_samples == 0:
        return np.zeros((0, n_components), dtype=np.float32)

    effective_neighbors = min(n_neighbors, max(2, n_samples - 1))
    effective_components = min(n_components, max(1, n_samples - 1))

    reducer = umap.UMAP(
        n_components=effective_components,
        metric=metric,
        n_neighbors=effective_neighbors,
        random_state=random_state,
    )
    return reducer.fit_transform(batch.raw).astype(np.float32)
