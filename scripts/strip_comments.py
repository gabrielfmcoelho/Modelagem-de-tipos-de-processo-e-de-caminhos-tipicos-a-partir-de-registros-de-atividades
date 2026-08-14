import argparse
import ast
import io
import subprocess
import sys
import tokenize
from pathlib import Path

DOC_NODES = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def iter_py_files(paths):
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(path.rglob("*.py"))
        elif path.suffix == ".py":
            yield path


def detect_newline(src):
    return "\r\n" if "\r\n" in src else "\n"


def is_preserved_comment(row, text):
    if row == 1 and text.startswith("#!"):
        return True
    if row in (1, 2) and ("coding:" in text or "coding=" in text):
        return True
    return False


def is_docstring_expr(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def doc_nodes_with_docstring(tree):
    for node in ast.walk(tree):
        if isinstance(node, DOC_NODES) and node.body and is_docstring_expr(node.body[0]):
            yield node


def comment_truncations(src):
    truncate = {}
    reader = io.StringIO(src).readline
    for tok in tokenize.generate_tokens(reader):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            if not is_preserved_comment(row, tok.string):
                truncate[row] = col
    return truncate


def docstring_targets(src):
    tree = ast.parse(src)
    delete_lines = set()
    pass_inserts = {}
    for node in doc_nodes_with_docstring(tree):
        doc = node.body[0]
        for line in range(doc.lineno, doc.end_lineno + 1):
            delete_lines.add(line)
        if len(node.body) == 1 and not isinstance(node, ast.Module):
            pass_inserts[doc.lineno] = doc.col_offset
    return delete_lines, pass_inserts


def strip_source(src):
    truncate = comment_truncations(src)
    delete_lines, pass_inserts = docstring_targets(src)
    newline = detect_newline(src)
    out = []
    for idx, line in enumerate(src.splitlines(keepends=True), start=1):
        if idx in delete_lines:
            if idx in pass_inserts:
                out.append(" " * pass_inserts[idx] + "pass" + newline)
            continue
        if idx in truncate:
            code = line[: truncate[idx]].rstrip()
            if code:
                out.append(code + newline)
            continue
        out.append(line)
    return "".join(out)


def find_violations(src):
    violations = []
    reader = io.StringIO(src).readline
    for tok in tokenize.generate_tokens(reader):
        if tok.type == tokenize.COMMENT and not is_preserved_comment(tok.start[0], tok.string):
            violations.append((tok.start[0], "comment"))
    for node in doc_nodes_with_docstring(ast.parse(src)):
        violations.append((node.body[0].lineno, "docstring"))
    return sorted(violations)


def normalize_tree(tree):
    for node in [n for n in ast.walk(tree) if isinstance(n, DOC_NODES)]:
        if node.body and is_docstring_expr(node.body[0]):
            del node.body[0]
            if not node.body and not isinstance(node, ast.Module):
                node.body.append(ast.Pass())
    return tree


def ast_signature(src):
    return ast.dump(normalize_tree(ast.parse(src)), include_attributes=False)


def git_show(rev, relpath):
    result = subprocess.run(
        ["git", "show", f"{rev}:{relpath}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def as_repo_path(path):
    path = Path(path)
    if path.is_absolute():
        return str(path.relative_to(Path.cwd()))
    return str(path)


def run_strip(paths):
    changed = 0
    for path in iter_py_files(paths):
        src = path.read_text(encoding="utf-8")
        stripped = strip_source(src)
        if stripped != src:
            path.write_text(stripped, encoding="utf-8")
            changed += 1
            print(f"stripped: {path}")
    print(f"files rewritten: {changed}")
    return 0


def run_check(paths):
    failures = 0
    for path in iter_py_files(paths):
        src = path.read_text(encoding="utf-8")
        for line, kind in find_violations(src):
            print(f"{path}:{line}: {kind}")
            failures += 1
    return 1 if failures else 0


def run_verify(original, stripped):
    a = Path(original).read_text(encoding="utf-8")
    b = Path(stripped).read_text(encoding="utf-8")
    if ast_signature(a) == ast_signature(b):
        print(f"verify OK: {original} == {stripped}")
        return 0
    print(f"verify MISMATCH: {original} != {stripped}")
    return 1


def run_verify_git(rev, paths):
    mismatches = 0
    checked = 0
    for path in iter_py_files(paths):
        relpath = as_repo_path(path)
        original = git_show(rev, relpath)
        if original is None:
            print(f"verify-git SKIP (not in {rev}): {relpath}")
            continue
        current = path.read_text(encoding="utf-8")
        checked += 1
        if ast_signature(original) != ast_signature(current):
            print(f"verify-git MISMATCH: {relpath}")
            mismatches += 1
    print(f"verify-git checked {checked} files, {mismatches} mismatch(es)")
    return 1 if mismatches else 0


def build_parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    p_strip = sub.add_parser("strip")
    p_strip.add_argument("paths", nargs="+")
    p_check = sub.add_parser("check")
    p_check.add_argument("paths", nargs="+")
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("original")
    p_verify.add_argument("stripped")
    p_vg = sub.add_parser("verify-git")
    p_vg.add_argument("rev")
    p_vg.add_argument("paths", nargs="+")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.mode == "strip":
        return run_strip(args.paths)
    if args.mode == "check":
        return run_check(args.paths)
    if args.mode == "verify":
        return run_verify(args.original, args.stripped)
    if args.mode == "verify-git":
        return run_verify_git(args.rev, args.paths)
    return 2


if __name__ == "__main__":
    sys.exit(main())
