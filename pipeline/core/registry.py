
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ._stage_base import Mode, StageFunc, StageMeta


@dataclass
class StageDef:
    meta: StageMeta
    func: StageFunc

    def call(self, ctx) -> None:
        self.func(ctx)


_REGISTRY: dict[str, StageDef] = {}


def stage(meta: StageMeta):
    def decorator(func: StageFunc) -> StageFunc:
        if meta.name in _REGISTRY:
            existing = _REGISTRY[meta.name]
            raise RuntimeError(
                f"Stage {meta.name!r} already registered (by {existing.func})"
            )
        _REGISTRY[meta.name] = StageDef(meta=meta, func=func)
        return func
    return decorator


def get(name: str) -> StageDef | None:
    return _REGISTRY.get(name)


def all_stages() -> list[StageDef]:
    return list(_REGISTRY.values())


def names() -> list[str]:
    return list(_REGISTRY.keys())


def clear() -> None:
    _REGISTRY.clear()


class StageNotFoundError(KeyError):
    pass


class CyclicDependencyError(RuntimeError):
    pass


class IncompatibleModeError(ValueError):
    pass


def resolve(names: Iterable[str], *, include_deps: bool = True) -> list[StageDef]:
    requested = list(names)
    for n in requested:
        if n not in _REGISTRY:
            raise StageNotFoundError(n)
    requested_set = set(requested)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    order: list[str] = []

    def visit(name: str) -> None:
        c = color.get(name, WHITE)
        if c == BLACK:
            return
        if c == GRAY:
            raise CyclicDependencyError(f"Cycle detected at {name!r}")
        color[name] = GRAY
        sd = _REGISTRY.get(name)
        if sd is None:
            raise StageNotFoundError(name)
        for dep in sd.meta.depends_on:
            if include_deps or dep in requested_set:
                visit(dep)
        color[name] = BLACK
        order.append(name)

    for n in requested:
        visit(n)

    return [_REGISTRY[n] for n in order]


def check_mode(stages: Iterable[StageDef], mode: Mode) -> list[str]:
    bad: list[str] = []
    for s in stages:
        if mode not in s.meta.modes:
            bad.append(s.meta.name)
    return bad


def soft_dep_warnings(stages: Iterable[StageDef]) -> list[tuple[str, str]]:
    selected_names = {s.meta.name for s in stages}
    warnings: list[tuple[str, str]] = []
    for s in stages:
        for soft in s.meta.soft_depends_on:
            if soft not in selected_names:
                warnings.append((s.meta.name, soft))
    return warnings
