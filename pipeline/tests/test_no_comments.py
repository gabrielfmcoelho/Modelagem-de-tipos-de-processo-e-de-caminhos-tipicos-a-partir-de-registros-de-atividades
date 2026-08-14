import ast
import io
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("pipeline", "reports", "scripts", "article/figures")
DOC_NODES = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _is_preserved_comment(row, text):
    if row == 1 and text.startswith("#!"):
        return True
    if row in (1, 2) and ("coding:" in text or "coding=" in text):
        return True
    return False


def _is_docstring_expr(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _violations(src):
    found = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT and not _is_preserved_comment(tok.start[0], tok.string):
            found.append((tok.start[0], "comment"))
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, DOC_NODES) and node.body and _is_docstring_expr(node.body[0]):
            found.append((node.body[0].lineno, "docstring"))
    return sorted(found)


def _iter_py():
    for name in SCAN_DIRS:
        base = ROOT / name
        if base.is_dir():
            yield from sorted(base.rglob("*.py"))


PY_FILES = list(_iter_py())


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_comments_or_docstrings(path):
    found = _violations(path.read_text(encoding="utf-8"))
    assert not found, f"{path.relative_to(ROOT)}: {found}"


def test_no_module_computes_its_own_repo_root():
    import importlib
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    third = {"httpx", "torch", "sklearn", "umap", "hdbscan", "neo4j", "leidenalg", "igraph",
             "dotenv", "trino", "pandas", "openai", "gliner2", "fitz", "PIL", "questionary",
             "typer", "rich", "pdf2image", "docx", "openpyxl", "matplotlib", "scipy", "pm4py"}
    wrong = []
    for f in sorted(repo.glob("pipeline/**/*.py")):
        if "__pycache__" in str(f) or "/tests/" in str(f):
            continue
        parts = list(f.relative_to(repo).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        try:
            mod = importlib.import_module(".".join(parts))
        except ModuleNotFoundError as e:
            if (e.name or "").split(".")[0] in third:
                continue
            raise
        for attr in ("ROOT", "_ROOT"):
            v = getattr(mod, attr, None)
            if isinstance(v, Path) and v.resolve() != repo:
                wrong.append(f"{'.'.join(parts)}.{attr} = {v}")
    assert not wrong, (
        "these modules expose a repository root that is not the repository root. Import "
        "ROOT from pipeline.core.paths instead of deriving it from file depth: "
        + "; ".join(wrong))


PACKAGE_DOCS = (
    "pipeline",
    "pipeline/core",
    "pipeline/model",
    "pipeline/stages",
    "pipeline/evidence",
    "pipeline/readers",
    "pipeline/writers",
    "pipeline/apps",
)


def test_every_architectural_package_explains_itself():
    missing = [f"{d}/{Path(d).name}.md" for d in PACKAGE_DOCS
               if not (ROOT / d / f"{Path(d).name}.md").is_file()]
    assert not missing, (
        "these packages carry no note saying why they exist and what they may import. The "
        "layering rule is only enforceable if it is written down next to the code it "
        "constrains: " + ", ".join(missing))


LAYER_OF = {
    "pipeline.core": "core",
    "pipeline.model": "model",
    "pipeline.readers": "io",
    "pipeline.writers": "io",
    "pipeline.evidence": "evidence",
    "pipeline.stages": "stages",
    "pipeline.apps": "apps",
}

MAY_IMPORT = {
    "core": {"core"},
    "model": {"core", "model"},
    "io": {"core", "io"},
    "evidence": {"core", "model", "evidence", "io"},
    "stages": {"core", "model", "io", "stages", "evidence"},
    "apps": {"core", "model", "io", "evidence", "stages", "apps"},
}

LAYER_EXCEPTIONS = {
    ("evidence", "stages"): ("evidence.artifact and evidence.stage_doc resolve the registry to "
                             "stamp; registration happens by import side effect, so the import "
                             "is local to a function and a top-level one would be a cycle"),
    ("core", "io"): ("core.runner selects the reader and writer from the stage's mode. It is "
                     "orchestration sitting in the plumbing layer, not a cycle — readers and "
                     "writers import core and never the runner. Recorded in "
                     "docs/architecture/pipeline-critique.md as a module to relocate"),
}


def _layer(mod: str) -> str | None:
    for prefix, layer in LAYER_OF.items():
        if mod == prefix or mod.startswith(prefix + "."):
            return layer
    return None


def test_the_layering_rule_is_obeyed():
    import importlib.util

    violations = []
    for f in sorted(ROOT.glob("pipeline/**/*.py")):
        if "__pycache__" in str(f) or "/tests/" in str(f):
            continue
        parts = list(f.relative_to(ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        mine = _layer(".".join(parts))
        if mine is None:
            continue
        pkg = ".".join(parts[:-1]) if len(parts) > 1 else ".".join(parts)
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    try:
                        base = importlib.util.resolve_name("." * node.level + base, pkg)
                    except (ImportError, ValueError):
                        continue
                targets = [base] + [f"{base}.{a.name}" for a in node.names]
            for t in targets:
                theirs = _layer(t)
                if theirs is None or theirs in MAY_IMPORT[mine]:
                    continue
                if (mine, theirs) in LAYER_EXCEPTIONS:
                    continue
                violations.append(
                    f"{f.relative_to(ROOT)}:{node.lineno}: {mine} imports {theirs} ({t})")
    assert not violations, (
        "the layering rule written in each package's .md is violated. core imports nothing, "
        "model imports core, io imports core, evidence imports core/model/io, stages import "
        "everything below them, apps import anything. The one accepted inversion is "
        "evidence -> stages for registry lookup: " + "; ".join(sorted(set(violations))))


COPYLEFT = ("pm4py",)


def test_no_copyleft_dependency_reaches_the_deployable_package():
    offenders = []
    for f in sorted(ROOT.glob("pipeline/**/*.py")):
        if "__pycache__" in str(f):
            continue
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module]
            for n in names:
                if n.split(".")[0] in COPYLEFT:
                    offenders.append(f"{f.relative_to(ROOT)}:{node.lineno}: imports {n}")
    assert not offenders, (
        "an AGPL dependency is imported from inside the deployable package. pm4py is confined "
        "to scripts/conformance_pm4py.py and reached by subprocess precisely so its licence "
        "does not attach to the pipeline; importing it here defeats that: "
        + "; ".join(offenders))


def test_no_stage_defaults_its_phase_silently():
    from pipeline import stages
    from pipeline.core import registry
    from pipeline.core._stage_base import PHASE_ORDER

    assert stages.__name__ == "pipeline.stages"
    allowed_default = {"artifact-audit", "clean", "graph-health", "resumo"}
    bad = [s.meta.name for s in registry.all_stages()
           if s.meta.phase == "operations" and s.meta.name not in allowed_default]
    assert not bad, (
        "these stages sit in the default phase 'operations'. A stage that actually belongs to "
        f"a pipeline phase must say so, or it vanishes from the generated phase view. "
        f"Valid phases: {', '.join(PHASE_ORDER)}. Offenders: " + ", ".join(sorted(bad)))


STAGE_REFERENCE_DOCS = (
    "docs/architecture/stage-registry.md",
    "docs/architecture/pipeline-overview.md",
    "docs/operations/running-stage-by-stage.md",
)


def test_every_registered_stage_appears_in_the_reference_docs():
    from pipeline import stages
    from pipeline.core import registry

    assert stages.__name__ == "pipeline.stages"
    names = sorted(registry.names())
    gaps = []
    for doc in STAGE_REFERENCE_DOCS:
        src = (ROOT / doc).read_text(encoding="utf-8")
        absent = [n for n in names if n not in src]
        if absent:
            gaps.append(f"{doc} omits {len(absent)}/{len(names)}: {', '.join(absent)}")
    assert not gaps, (
        "a registered stage exists that these reference docs never mention, so the only way to "
        "discover it is to read the registry: " + "; ".join(gaps))


DOC_HISTORY = ("docs/superpowers/", "docs/paper/reviews/")


def test_live_docs_do_not_name_a_python_file_that_moved():
    import re

    pat = re.compile(r"\bpipeline/[A-Za-z0-9_/]+\.py\b")
    dangling = []
    for md in sorted(ROOT.glob("docs/**/*.md")):
        rel = str(md.relative_to(ROOT))
        if any(rel.startswith(h) for h in DOC_HISTORY):
            continue
        block, start = [], 1
        lines = md.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines + [""], 1):
            if line.strip():
                if not block:
                    start = i
                block.append(line)
                continue
            para = "\n".join(block)
            if block and "deleted in commit" not in para:
                for ref in pat.findall(para):
                    if not (ROOT / ref).is_file():
                        dangling.append(f"{rel}:{start}: {ref}")
            block = []
    assert not dangling, (
        "these live docs point a reader at a module that does not exist. Historical records "
        f"under {' and '.join(DOC_HISTORY)} are exempt, as is any line that says 'deleted in "
        "commit <sha>' — naming a dead module is fine as long as the doc says when it died: "
        + "; ".join(dangling))


def test_no_package_init_is_shadowed_by_its_own_reexports():
    clashes = []
    for init in sorted(ROOT.glob("pipeline/**/__init__.py")):
        if "__pycache__" in str(init):
            continue
        tree = ast.parse(init.read_text(encoding="utf-8"))
        assigned, reexported = {}, {}
        for node in tree.body:
            targets = []
            if isinstance(node, ast.AnnAssign):
                targets = [node.target]
            elif isinstance(node, ast.Assign):
                targets = node.targets
            for t in targets:
                if isinstance(t, ast.Name) and t.id != "__all__":
                    assigned.setdefault(t.id, node.lineno)
            if isinstance(node, ast.ImportFrom) and node.level:
                for a in node.names:
                    reexported.setdefault(a.asname or a.name, node.lineno)
        for name in sorted(assigned.keys() & reexported.keys()):
            if reexported[name] > assigned[name]:
                clashes.append(
                    f"{init.relative_to(ROOT)}: {name} defined at line {assigned[name]} is "
                    f"overwritten by the re-export at line {reexported[name]}")
    assert not clashes, (
        "a package __init__ defines a name and then imports a different value under the same "
        "name from a submodule; every consumer silently gets the later one. This is how "
        "precreate came to create the 5 NER constraints instead of the 28 schema ones: "
        + "; ".join(clashes))


def _file_depth(node, known):
    if isinstance(node, ast.Name):
        return known.get(node.id)
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        base = _file_depth(node.value, known)
        return None if base is None else base + 1
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "resolve":
            return _file_depth(f.value, known)
        if isinstance(f, ast.Name) and f.id == "Path" and len(node.args) == 1:
            a = node.args[0]
            return 0 if isinstance(a, ast.Name) and a.id == "__file__" else None
    return None


def test_scripts_outside_the_package_anchor_the_repo_root_correctly():
    wrong = []
    for name in ("reports", "scripts", "article/figures"):
        base = ROOT / name
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.py")):
            if "__pycache__" in str(f):
                continue
            rel = f.relative_to(ROOT)
            known = {}
            for node in ast.parse(f.read_text(encoding="utf-8")).body:
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                depth = _file_depth(node.value, known)
                if depth is None:
                    continue
                known[target.id] = depth
                if target.id in ("ROOT", "_ROOT") and depth != len(rel.parts):
                    wrong.append(
                        f"{rel}:{node.lineno}: {target.id} climbs {depth} level(s) but the file "
                        f"sits {len(rel.parts)} deep")
    assert not wrong, (
        "these scripts derive the repository root from file depth and get it wrong; they will "
        "read and write artifacts outside the repo. They cannot import pipeline.core.paths "
        "without side effects, so the arithmetic is checked here: " + "; ".join(wrong))


def test_module_paths_passed_as_strings_resolve():
    import ast
    import importlib.util
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    offenders = []
    for f in sorted(repo.glob("pipeline/**/*.py")):
        if "__pycache__" in str(f):
            continue
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if not isinstance(n, ast.Constant) or not isinstance(n.value, str):
                continue
            v = n.value
            if not v.startswith("pipeline.") or " " in v or "/" in v:
                continue
            parts = v.split(".")
            resolved = False
            for k in range(len(parts), 1, -1):
                target = repo / Path(*parts[:k])
                if target.with_suffix(".py").is_file() or (target / "__init__.py").is_file():
                    resolved = True
                    break
            if not resolved:
                offenders.append(f"{f.relative_to(repo)}:{n.lineno}: {v!r}")
    assert not offenders, (
        "these string literals name a module that does not exist; they are invisible to import "
        "checking and fail only when the line executes: " + "; ".join(offenders))


def test_the_package_imports_and_the_registry_is_complete():
    from pipeline import stages
    from pipeline.core import registry

    assert stages.__name__ == "pipeline.stages"
    names = registry.names()
    assert len(names) >= 47, (
        f"only {len(names)} stages registered. A package that does not import cannot be "
        "caught by compilation or by static name resolution — this test is the one that "
        "would have caught the orphan @dataclass decorators of 2026-08-06.")
    assert len(names) == len(set(names)), "duplicate stage names in the registry"


def test_every_module_with_a_main_can_be_run_with_dash_m():
    import ast
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    offenders = []
    for f in sorted(repo.glob("pipeline/**/*.py")):
        if "__pycache__" in str(f) or "/tests/" in str(f):
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        has_main = any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body)
        has_guard = any(isinstance(n, ast.If) and "__main__" in ast.unparse(n.test)
                        for n in tree.body)
        if has_main and not has_guard:
            offenders.append(str(f.relative_to(repo)))
    assert not offenders, (
        "these modules define main() but have no __main__ guard, so `python -m <module>` "
        "imports them and exits 0 without running anything — a subprocess caller reads that "
        "as success while nothing was produced: " + "; ".join(offenders))


def test_every_model_list_covers_the_registered_models():
    from pipeline.evidence.compose.lattice import MODELS as compose_models
    from pipeline.evidence.typical_path.blocks import MODELS as block_models
    from pipeline.evidence.typical_path.figures import GEN_MODEL as gen_models
    from pipeline.evidence.typical_path.figures import MODELS as figure_models
    from pipeline.evidence.typical_path.tables import MODELS as table_models
    from pipeline.model.typical_eval import MODEL_NAMES
    from pipeline.model.typical_path import MODEL_NAMES as reexport
    from pipeline.stages.noninferiority import MODELS as noninf_models

    lists = {"evidence.figures": figure_models, "evidence.figures GEN_MODEL": gen_models, "evidence.tables": table_models,
             "evidence.blocks": block_models, "compose.lattice": compose_models,
             "stages.noninferiority": noninf_models, "typical_path re-export": reexport}
    bad = {n: sorted(set(MODEL_NAMES) - set(v)) for n, v in lists.items()
           if set(v) != set(MODEL_NAMES)}
    assert not bad, (
        "a model is registered in typical_eval.MODEL_NAMES but missing from a downstream list. "
        "Each cell would carry its metrics and every table and figure would silently ignore "
        "them — which is exactly what happened when `gnn` was added: " + repr(bad))


def _string_groups(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            vals = [e.value for e in node.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if node.elts and len(vals) == len(node.elts) and len(vals) >= 2:
                yield node.lineno, vals
        elif isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            if node.keys and len(keys) == len(node.keys) and len(keys) >= 2:
                yield node.lineno, keys
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            parts = [p.strip() for p in node.value.split(",")]
            if len(parts) >= 2:
                yield node.lineno, parts


def _registries():
    from pipeline.model.typical_eval import ALPHABET_NAMES, MODEL_NAMES
    return {"MODEL_NAMES": MODEL_NAMES, "ALPHABET_NAMES": ALPHABET_NAMES}


REGISTRY_PARTIAL_BY_DESIGN = {
    ("pipeline/evidence/typical_path/constraint_cost.py", ("itinerary", "procedure")):
        "unit is the base alphabet, not a projection of one, so it has no transform function",
    ("scripts/conformance_pm4py.py", ("procedure", "unit")):
        "pm4py conformance is offered only on the alphabets whose states carry a lane; "
        "widening it to itinerary is a semantic question, not a list to keep in sync",
    ("reports/gen_14_explorer.py", ("gru", "markov")):
        "the explorer deliberately contrasts one neural family against the baseline",
}


@pytest.mark.parametrize("registry", sorted(_registries()))
def test_no_literal_reimplements_a_registry_incompletely(registry):
    names = set(_registries()[registry])
    offenders = []
    for path in PY_FILES:
        if "tests" in path.parts:
            continue
        rel = str(path.relative_to(ROOT))
        for lineno, vals in _string_groups(ast.parse(path.read_text(encoding="utf-8"))):
            hits = names & set(vals)
            if len(hits) < 2 or names <= set(vals):
                continue
            if (rel, tuple(sorted(vals))) in REGISTRY_PARTIAL_BY_DESIGN:
                continue
            offenders.append(f"{rel}:{lineno} has {sorted(hits)} but "
                             f"omits {sorted(names - set(vals))}")
    assert not offenders, (
        f"a literal enumerates part of {registry} without covering it. Importing the registry "
        "is the only way a new member reaches every consumer; the previous guard listed the "
        "seven lists it knew about, so the eighth was missing `gnn` and nothing noticed. "
        "Extra entries are fine — coverage is what is checked: " + "; ".join(offenders))
