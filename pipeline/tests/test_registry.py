from __future__ import annotations

import pytest

from ..core import registry
from ..core._stage_base import StageMeta


@pytest.fixture
def isolated_registry():
    saved = dict(registry._REGISTRY)
    registry.clear()
    try:
        yield
    finally:
        registry._REGISTRY.clear()
        registry._REGISTRY.update(saved)


def _register(name, deps=()):
    @registry.stage(StageMeta(name=name, description="", type="core",
                              depends_on=tuple(deps), modes=("neo4j",)))
    def _run(ctx):
        pass
    return _run


def test_resolve_pulls_in_transitive_deps(isolated_registry):
    _register("a")
    _register("b", deps=("a",))
    assert [s.meta.name for s in registry.resolve(["b"])] == ["a", "b"]


def test_no_deps_runs_only_the_named_stage(isolated_registry):
    _register("a")
    _register("b", deps=("a",))
    assert [s.meta.name for s in registry.resolve(["b"], include_deps=False)] == ["b"]


def test_no_deps_still_orders_named_stages_topologically(isolated_registry):
    _register("a")
    _register("b", deps=("a",))
    assert [s.meta.name for s in registry.resolve(["b", "a"], include_deps=False)] == ["a", "b"]


def test_no_deps_unknown_name_raises(isolated_registry):
    with pytest.raises(registry.StageNotFoundError):
        registry.resolve(["nope"], include_deps=False)
