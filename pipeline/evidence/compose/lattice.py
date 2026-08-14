from __future__ import annotations

from dataclasses import dataclass, field

from ...model.typical_eval import ALPHABET_NAMES as ALPHABETS, MODEL_NAMES as MODELS

ARMS = ("raw", "anon")
ALGOS = ("hdbscan", "kmeans", "leiden")

BASE_PARAM = "base"
CONTROL_SUFFIX = "shuffled"
ABLATION_PARAMS = ("cut0.25", "cut0.5", "cut0.75", "nokeyword", "notopic")
SELECTION_PARAMS = ("kelbow", "ksil", "lres", "hcoarse")

LEVELS = {
    "L0": (),
    "L1": ("arm",),
    "L2": ("arm", "param", "algo"),
    "L3": ("arm", "param", "algo", "alphabet"),
    "L4": ("arm", "param", "algo", "alphabet", "model"),
    "L5": ("arm", "param", "algo", "alphabet", "cluster"),
}


@dataclass(frozen=True)
class Coord:
    run_id: str
    arm: str
    param: str
    control: bool
    ablation: bool
    algo: str = ""
    alphabet: str = ""
    model: str = ""
    cluster: str = ""
    extra: dict = field(default_factory=dict)

    def scope(self, level: str) -> dict:
        axes = LEVELS[level]
        out = {"level": level}
        for a in axes:
            out[a] = getattr(self, a)
        out["run_id"] = self.run_id
        if self.control:
            out["control"] = True
        if self.ablation:
            out["ablation"] = True
        return out


def parse_run_id(run_id: str) -> Coord:
    rest = run_id
    for prefix in ("exp-anon", "exp-raw"):
        if rest == prefix or rest.startswith(prefix + "-"):
            arm = "anon" if prefix == "exp-anon" else "raw"
            tail = rest[len(prefix):].lstrip("-")
            param = tail or BASE_PARAM
            return Coord(
                run_id=run_id,
                arm=arm,
                param=param,
                control=param == CONTROL_SUFFIX,
                ablation=param in ABLATION_PARAMS,
            )
    return Coord(run_id=run_id, arm="unknown", param=run_id, control=False, ablation=False)


def coord_of_cell(cell: dict) -> Coord:
    base = parse_run_id(cell["run_id"])
    return Coord(
        run_id=base.run_id,
        arm=base.arm,
        param=base.param,
        control=base.control or bool(cell.get("control")),
        ablation=base.ablation,
        algo=cell.get("algo", ""),
        alphabet=cell.get("alphabet", ""),
    )


def cell_key(cell: dict) -> str:
    return f"{cell['run_id']}/{cell['algo']}/{cell['alphabet']}"


def expected_members(cells: list[dict], **fixed) -> tuple[list[str], list[str]]:
    present = []
    for c in cells:
        co = coord_of_cell(c)
        if all(getattr(co, k) == v for k, v in fixed.items()):
            present.append(cell_key(c))
    return sorted(present), []


def main_cells(cells: list[dict]) -> list[dict]:
    out = []
    for c in cells:
        co = coord_of_cell(c)
        if co.control or co.ablation:
            continue
        out.append(c)
    return out
