#!/usr/bin/env python
from __future__ import annotations

import argparse
import ast
import importlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DESCRIPTION = (
    "Probe every registered stage and every artifact on disk, reporting what is actually true "
    "rather than what a test asserts. Reads only; runs nothing."
)

WRITERS = ("write_artifact", "write_sidecar")
ARTIFACT_HINTS = ("ARTIFACTS", "artifacts/", '"artifacts"')


def _module_of(stage_def) -> str:
    return getattr(stage_def.func, "__module__", "")


def _source(mod_name: str) -> tuple[Path | None, str]:
    try:
        mod = importlib.import_module(mod_name)
    except Exception:
        return None, ""
    f = getattr(mod, "__file__", None)
    if not f:
        return None, ""
    p = Path(f)
    return p, p.read_text(encoding="utf-8")


def _calls(src: str, names) -> set[str]:
    found = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            n = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if n in names:
                found.add(n)
    return found


def _imported_pipeline_modules(src: str, mod_name: str) -> set[str]:
    import importlib.util
    out: set[str] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    pkg = mod_name.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names if a.name.startswith("pipeline")}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            try:
                resolved = (importlib.util.resolve_name("." * node.level + base, pkg)
                            if node.level else base)
            except (ImportError, ValueError):
                continue
            if not resolved.startswith("pipeline"):
                continue
            out.add(resolved)
            out |= {f"{resolved}.{a.name}" for a in node.names}
    return out


def _reaches(src: str, mod_name: str, depth: int = 2) -> set[str]:
    found = _calls(src, WRITERS)
    seen = {mod_name}
    frontier = [(src, mod_name)]
    for _ in range(depth):
        if found:
            break
        nxt = []
        for s, name in frontier:
            for target in _imported_pipeline_modules(s, name):
                if target in seen:
                    continue
                seen.add(target)
                _, sub = _source(target)
                if not sub:
                    continue
                found |= _calls(sub, WRITERS)
                nxt.append((sub, target))
        frontier = nxt
    return found


RAW_WRITES = ("write_text", "savez_compressed", "savez", "dump", "savefig")

LLM_CALLS = ("_get_client", "build_embedder")
GPU_MODULES = ("torch", "torch_geometric")


def _raw_writes(src: str) -> set[str]:
    return _calls(src, RAW_WRITES)


def _stamp_calls(src: str) -> tuple[int, int]:
    total = with_inputs = 0
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0, 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if fn in WRITERS:
                total += 1
                if any(k.arg == "inputs" for k in node.keywords):
                    with_inputs += 1
    return total, with_inputs


def _reachable_source(mod_name: str, depth: int = 2) -> str:
    _, blob = _source(mod_name)
    seen, frontier = {mod_name}, [(blob, mod_name)]
    for _ in range(depth):
        nxt = []
        for s, name in frontier:
            for target in _imported_pipeline_modules(s, name):
                if target in seen:
                    continue
                seen.add(target)
                _, sub = _source(target)
                if sub:
                    blob += sub
                    nxt.append((sub, target))
        frontier = nxt
    return blob


def _is_global_rng(fn) -> bool:
    owner = getattr(fn, "value", None)
    if getattr(owner, "id", None) == "random":
        return getattr(fn, "attr", None) != "seed"
    return (getattr(owner, "attr", None) == "random"
            and getattr(getattr(owner, "value", None), "id", None) in ("np", "numpy"))


def _randomness_ast(mod_name: str, hops: int = 1) -> list[str]:
    found: set[str] = set()
    seen, frontier = {mod_name}, [mod_name]
    for _ in range(hops + 1):
        nxt = []
        for name in frontier:
            _, src = _source(name)
            if not src or name.startswith("pipeline.core."):
                continue
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[0] in GPU_MODULES for a in node.names):
                        found.add("imports-torch")
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    if (node.module or "").split(".")[0] in GPU_MODULES:
                        found.add("imports-torch")
                elif isinstance(node, ast.Call):
                    fn = node.func
                    attr = getattr(fn, "attr", None)
                    if (getattr(fn, "id", None) in LLM_CALLS) or (attr in LLM_CALLS):
                        found.add("llm-call")
                    if _is_global_rng(fn):
                        found.add("unseeded-rng")
            for target in _imported_pipeline_modules(src, name):
                if target not in seen:
                    seen.add(target)
                    nxt.append(target)
        frontier = nxt
    return sorted(found)


def probe_stages() -> list[dict]:
    import pipeline.stages
    from pipeline.core import registry

    assert pipeline.stages.__name__ == "pipeline.stages"

    rows = []
    for sd in sorted(registry.all_stages(), key=lambda s: (s.meta.phase, s.meta.name)):
        m = sd.meta
        mod_name = _module_of(sd)
        path, src = _source(mod_name)
        rows.append({
            "stage": m.name,
            "phase": m.phase,
            "type": m.type,
            "deterministic": m.deterministic,
            "has_question": bool(m.question),
            "has_nondeterminism_note": (m.deterministic is True) or bool(m.nondeterminism),
            "modes": ",".join(m.modes),
            "depends_on": ",".join(m.depends_on),
            "module": mod_name,
            "loc": len(src.splitlines()) if src else 0,
            "touches_artifacts": any(h in src for h in ARTIFACT_HINTS),
            "raw_writes": sorted(_raw_writes(src)),
            "stamps": sorted(_reaches(src, mod_name)),
            "stamp_calls": _stamp_calls(_reachable_source(mod_name))[0],
            "stamps_with_inputs": _stamp_calls(_reachable_source(mod_name))[1],
            "randomness": (_randomness_ast(mod_name) if m.deterministic is True else []),
            "has_main_guard": "__main__" in src,
        })
    return rows


def probe_artifacts() -> list[dict]:
    from pipeline.evidence.artifact import META_KEY, inputs_match, sidecar_path

    root = _ROOT / "artifacts"
    rows = []
    if not root.is_dir():
        return rows
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.name.endswith(".meta.json"):
            continue
        rel = str(f.relative_to(root))
        stage = drift = None
        if f.suffix == ".json":
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                meta = d.get(META_KEY) if isinstance(d, dict) else None
            except Exception:
                meta = None
            stamped = meta is not None
            if stamped:
                stage = meta.get("stage")
                drift = inputs_match(f) or None
        else:
            side = sidecar_path(f)
            stamped = side.is_file()
            if stamped:
                try:
                    stage = json.loads(side.read_text(encoding="utf-8"))[META_KEY]["stage"]
                except Exception:
                    stage = "?"
        rows.append({"artifact": rel, "bytes": f.stat().st_size,
                     "stamped": stamped, "stage": stage, "drift": drift})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    stages = probe_stages()
    artifacts = probe_artifacts()

    if args.json:
        print(json.dumps({"stages": stages, "artifacts": artifacts}, indent=2, ensure_ascii=False))
        return 0

    print(f"STAGES ({len(stages)})\n")
    print(f"  {'stage':<20} {'phase':<13} {'det':<12} {'loc':>5}  {'stamps':<24} flags")
    print("  " + "-" * 96)
    phase = None
    for r in stages:
        if r["phase"] != phase:
            phase = r["phase"]
            print(f"  ── {phase}")
        flags = []
        if not r["has_question"]:
            flags.append("NO-QUESTION")
        if not r["has_nondeterminism_note"]:
            flags.append("NO-NONDET-NOTE")
        if r["touches_artifacts"] and r["raw_writes"] and not r["stamps"]:
            flags.append("RAW-WRITE-NO-STAMP")
        if r["stamp_calls"] == 0:
            flags.append("NO-ARTIFACT")
        elif r["stamps_with_inputs"] == 0:
            flags.append("NO-INPUTS-DECLARED")
        if r["randomness"]:
            flags.append("DET-TRUE-BUT=" + ",".join(r["randomness"]))
        print(f"  {r['stage']:<20} {r['phase']:<13} {str(r['deterministic']):<12} {r['loc']:>5}  "
              f"{','.join(r['stamps']) or '-':<24} {' '.join(flags)}")

    n_q = sum(1 for r in stages if not r["has_question"])
    n_n = sum(1 for r in stages if not r["has_nondeterminism_note"])
    n_u = sum(1 for r in stages if r["touches_artifacts"] and r["raw_writes"] and not r["stamps"])
    n_noart = sum(1 for r in stages if r["stamp_calls"] == 0)
    n_noin = sum(1 for r in stages if r["stamp_calls"] and not r["stamps_with_inputs"])
    n_rand = sum(1 for r in stages if r["randomness"])
    print(f"\n  missing question: {n_q} | missing nondeterminism note: {n_n} | "
          f"raw-write into artifacts with no stamper in reach: {n_u}")
    print(f"  emit NO artifact: {n_noart}/{len(stages)} | stamp but declare no inputs: {n_noin} "
          f"| declared deterministic yet reach randomness: {n_rand}")

    print(f"\n\nARTIFACTS ({len(artifacts)})\n")
    if not artifacts:
        print("  none on disk.")
    else:
        print(f"  {'artifact':<52} {'bytes':>10}  {'stamped':<8} stage")
        print("  " + "-" * 96)
        for r in artifacts:
            mark = "yes" if r["stamped"] else "NO"
            drift = f"  DRIFT {r['drift']}" if r["drift"] else ""
            print(f"  {r['artifact']:<52} {r['bytes']:>10}  {mark:<8} {r['stage'] or '-'}{drift}")
        n_bad = sum(1 for r in artifacts if not r["stamped"])
        n_drift = sum(1 for r in artifacts if r["drift"])
        print(f"\n  unstamped: {n_bad} | drifted: {n_drift}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
