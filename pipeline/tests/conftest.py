import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

_ARTIFACTS = SCRIPTS_DIR / "artifacts"


def _artifact_manifest() -> dict[str, tuple[int, int]]:
    if not _ARTIFACTS.is_dir():
        return {}
    out = {}
    for p in _ARTIFACTS.rglob("*"):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(SCRIPTS_DIR))] = (st.st_mtime_ns, st.st_size)
    return out


@pytest.fixture(scope="session", autouse=True)
def artifacts_stay_read_only():
    before = _artifact_manifest()
    yield
    after = _artifact_manifest()
    touched = sorted(
        set(before) ^ set(after)
        | {k for k in before.keys() & after.keys() if before[k] != after[k]})
    assert not touched, (
        "the test session wrote into the real artifacts tree. A module-level path constant "
        "escaped monkeypatching and overwrote evidence with fixture data — this is how "
        "artifacts/cache/tipo_procedimento.json was clobbered on 2026-08-10. Patch the "
        "constant in the test, do not relax this guard: " + "; ".join(touched))
