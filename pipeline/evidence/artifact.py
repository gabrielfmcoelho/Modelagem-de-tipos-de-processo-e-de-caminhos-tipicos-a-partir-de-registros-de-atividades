from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from ..core.state import now_iso, record_write as _record

from ..core.paths import ROOT
META_KEY = "_meta"

_TRACKED = ("numpy", "scikit-learn", "hdbscan", "umap-learn", "igraph", "leidenalg",
            "torch", "neo4j")


def _versions() -> dict[str, str]:
    import importlib.metadata as md
    out: dict[str, str] = {}
    for dist in _TRACKED:
        try:
            out[dist] = md.version(dist)
        except Exception:
            continue
    return out


def _commit() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                           text=True, timeout=5, check=False)
    except Exception:
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def digest(path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def build_meta(stage: str, *, params: dict | None = None, inputs=()) -> dict:
    from ..core import registry
    from .. import stages
    meta = registry.get(stage)
    if meta is None:
        raise ValueError(
            f"write_artifact: {stage!r} is not a registered stage. Every artifact must name the "
            "stage that produced it, so that its question and its determinism can be read off "
            "the registry rather than guessed.")
    m = meta.meta
    return {
        "stage": stage,
        "question": m.question,
        "deterministic": m.deterministic,
        "nondeterminism": m.nondeterminism or None,
        "generated_at": now_iso(),
        "commit": _commit(),
        "params": dict(params or {}),
        "inputs": [{"path": _rel(p), "sha256": digest(p)} for p in inputs],
        "versions": _versions(),
    }


def sidecar_path(path) -> Path:
    p = Path(path)
    return p.with_name(p.name + ".meta.json")


def write_sidecar(path, *, stage: str, params: dict | None = None, inputs=()) -> Path:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(
            f"write_sidecar: {target} does not exist. Write the artifact first, then stamp it — "
            "the sidecar records the sha256 of the bytes actually on disk.")
    side = sidecar_path(target)
    body = {
        META_KEY: build_meta(stage, params=params, inputs=inputs),
        "describes": _rel(target),
        "sha256": digest(target),
        "bytes": target.stat().st_size,
    }
    side.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    record_write(target, stage=stage, meta=body[META_KEY])
    return side


def write_artifact(payload: dict, path, *, stage: str, params: dict | None = None,
                   inputs=(), force: bool = True) -> Path:
    out = Path(path)
    if out.exists() and not force:
        raise FileExistsError(
            f"{out} already exists; pass force=True to overwrite (frozen artifacts must not "
            "be clobbered)")
    meta = build_meta(stage, params=params, inputs=inputs)
    body = {META_KEY: meta, **payload}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    record_write(out, stage=stage, meta=meta)
    return out


def read_meta(path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8")).get(META_KEY) or {}


def inputs_match(path) -> list[str]:
    meta = read_meta(path)
    drifted = []
    for rec in meta.get("inputs") or []:
        want = rec.get("sha256")
        got = digest(ROOT / rec["path"])
        if want != got:
            drifted.append(rec["path"])
    return drifted


def record_write(path, *, stage: str, meta: dict) -> None:
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError:
        size = None
    _record(_rel(p), stage=stage, size=size, inputs=meta.get("inputs") or [])
