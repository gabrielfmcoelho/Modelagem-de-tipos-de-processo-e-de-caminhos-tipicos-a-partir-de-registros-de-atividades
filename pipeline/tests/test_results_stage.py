from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..core._stage_base import RunContext
from ..core.config import Settings
from ..evidence.clustering import tables as ctab
from ..evidence.results import results_tex
from ..evidence.typical_path import tables as ttab
from pipeline.stages import results as st


def _patch(monkeypatch, load):
    monkeypatch.setattr(st, "results_figures", load("results_figures"))
    monkeypatch.setattr(st, "results_doc", load("gen_results"))
    monkeypatch.setattr(st, "results_tex", load("gen_tables_tex"))


def _ctx(tmp_path, **flags):
    flags.setdefault("tables", str(tmp_path / "tables"))
    flags.setdefault("tables_pt", str(tmp_path / "tables-pt"))
    return RunContext(settings=Settings.from_env(), mode="fs", flags=flags,
                      state_dir=tmp_path)


def _doc(tmp_path, blocks, body="STALE"):
    d = tmp_path / "R.md"
    d.write_text("\n\n".join(f"<!-- fig:{b} -->\n{body}\n<!-- /fig:{b} -->" for b in blocks),
                 encoding="utf-8")
    return d


def test_stage_is_registered():
    import pipeline.stages
    from ..core import registry
    assert "results" in registry.names()


def test_refuses_to_run_with_no_matrix_cells(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(0))
    with pytest.raises(RuntimeError, match="no matrix cells"):
        st.run(_ctx(tmp_path, doc=str(_doc(tmp_path, ["a"])), figures=str(tmp_path / "f.json")))


def test_refuses_when_the_doc_is_missing_markers(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    doc = tmp_path / "R.md"
    doc.write_text("no markers here\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing markers"):
        st.run(_ctx(tmp_path, doc=str(doc), figures=str(tmp_path / "f.json")))


def test_writes_figures_and_regenerates_the_doc(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    doc = _doc(tmp_path, ["a"])
    fig = tmp_path / "f.json"
    ctx = _ctx(tmp_path, doc=str(doc), figures=str(fig))
    st.run(ctx)
    assert "STALE" not in doc.read_text(encoding="utf-8")
    assert json.loads(fig.read_text(encoding="utf-8"))["n_cells"] == 3
    assert ctx.cache["results_summary"]["blocks"] == 1


def test_check_mode_fails_on_drift_and_writes_nothing(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    doc = _doc(tmp_path, ["a"])
    fig = tmp_path / "f.json"
    with pytest.raises(RuntimeError, match="out of date"):
        st.run(_ctx(tmp_path, doc=str(doc), figures=str(fig), check="true"))
    assert "STALE" in doc.read_text(encoding="utf-8")
    assert not fig.exists()


def test_check_mode_passes_when_up_to_date(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    doc = _doc(tmp_path, ["a"])
    fig = tmp_path / "f.json"
    st.run(_ctx(tmp_path, doc=str(doc), figures=str(fig)))
    ctx = _ctx(tmp_path, doc=str(doc), figures=str(fig), check="true")
    st.run(ctx)
    assert ctx.cache["results_summary"]["checked"] is True
    assert ctx.cache["results_summary"]["latex_tables"] == 2


def test_check_mode_fails_when_a_latex_table_drifts(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    doc = _doc(tmp_path, ["a"])
    fig = tmp_path / "f.json"
    st.run(_ctx(tmp_path, doc=str(doc), figures=str(fig)))
    table = tmp_path / "tables" / "demo.tex"
    table.write_text(table.read_text(encoding="utf-8").replace("x", "999"), encoding="utf-8")
    with pytest.raises(RuntimeError, match="demo"):
        st.run(_ctx(tmp_path, doc=str(doc), figures=str(fig), check="true"))


def test_check_mode_fails_when_the_ptbr_table_drifts(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    doc = _doc(tmp_path, ["a"])
    fig = tmp_path / "f.json"
    st.run(_ctx(tmp_path, doc=str(doc), figures=str(fig)))
    table = tmp_path / "tables-pt" / "demo.tex"
    table.write_text("edited by hand\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="tables-pt"):
        st.run(_ctx(tmp_path, doc=str(doc), figures=str(fig), check="true"))


def test_a_table_with_no_pt_entry_is_reported(tmp_path, monkeypatch, caplog):
    class _Gappy(_FakeTex):
        @staticmethod
        def untranslated(body):
            return {"untranslated header": ["untranslated", "header"]}

    def _load(name):
        if name == "results_figures":
            return _FakeRF(3)
        if name == "gen_tables_tex":
            return _Gappy()
        return _FakeGR()

    _patch(monkeypatch, _load)
    with caplog.at_level("WARNING"):
        st.run(_ctx(tmp_path, doc=str(_doc(tmp_path, ["a"])), figures=str(tmp_path / "f.json")))
    assert "untranslated header" in caplog.text


def test_ptbr_tables_use_brazilian_numeric_separators():
    tex = results_tex
    body = tex.to_pt(
        "\\caption{Right-censoring by opening month.}\\label{tab:corpus-bias}\n"
        "\\begin{tabular}{p{0.42\\textwidth}rr}\n"
        "month & observed \\\\\n"
        "Observed 5{,}243 and 20,000 draws, 0.726 and 18.2\\%, Section 4.7 (§7.1)\n")
    assert "0,726" in body and "18,2" in body
    assert "5.243" in body and "20.000" in body
    assert "tab:corpus-bias" in body and "p{0.42\\textwidth}" in body
    assert "Section 4.7" in body and "§7.1" in body
    assert "mês" in body and "observados" in body


def test_untranslated_strings_are_reported_not_skipped():
    tex = results_tex
    body = ("\\caption{A caption nobody translated.}\\label{tab:x}\n"
            "\\toprule\nmonth & untranslated header \\\\\n\\midrule\n")
    gaps = tex.untranslated(body)
    assert gaps["A caption nobody translated."]
    assert gaps["untranslated header"]
    assert "month" not in gaps


def test_the_body_tables_are_fully_translated():
    tex = results_tex
    if not st.FIGURES_PATH.is_file():
        pytest.skip(f"{st.FIGURES_PATH.name} absent — run `pipeline run results` after a matrix "
                    "sweep. This checks rendered output, so it has nothing to render against.")
    figures = json.loads(st.FIGURES_PATH.read_text(encoding="utf-8"))
    for name in ("corpus-bias", "taxonomy", "catalogue", "ablation", "common-set",
                 "index-mechanism", "controls", "selection"):
        assert tex.untranslated(tex.TABLES[name](figures)) == {}, name


def test_check_mode_fails_when_the_latex_tables_are_absent(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    doc = _doc(tmp_path, ["a"], body="RENDERED")
    with pytest.raises(RuntimeError, match="out of date"):
        st.run(_ctx(tmp_path, doc=str(doc), figures=str(tmp_path / "f.json"), check="true"))


class _FakeTex:
    TABLES = {"demo": lambda f: "\\begin{tabular}{l}x 1,234 5.6\\end{tabular}"}
    HEADER = "%% GENERATED\n"

    @staticmethod
    def to_pt(body):
        return body.replace("x", "xis").replace("1,234", "1.234").replace("5.6", "5,6")

    @staticmethod
    def untranslated(body):
        return {}


def _fake_loader(n):
    def _load(name):
        if name == "results_figures":
            return _FakeRF(n)
        if name == "gen_tables_tex":
            return _FakeTex()
        return _FakeGR()
    return _load


class _FakeRF:
    def __init__(self, n):
        self.n = n

    def build(self):
        return {"n_cells": self.n, "model_count": {"models_trained": 10}, "cluster_counts": {}}


class _FakeGR:
    BLOCKS = {"a": lambda f: "RENDERED"}

    @staticmethod
    def render(doc, figures):
        filled = []
        out = doc
        for name in _FakeGR.BLOCKS:
            marker_open, marker_close = f"<!-- fig:{name} -->", f"<!-- /fig:{name} -->"
            if marker_open in doc and marker_close in doc:
                import re
                out = re.sub(rf"{re.escape(marker_open)}.*?{re.escape(marker_close)}",
                             f"{marker_open}\nRENDERED\n{marker_close}", out, flags=re.DOTALL)
                filled.append(name)
        return out, filled


def test_latex_tables_are_written_alongside_the_markdown(tmp_path, monkeypatch):
    _patch(monkeypatch, _fake_loader(3))
    ctx = _ctx(tmp_path, doc=str(_doc(tmp_path, ["a"])), figures=str(tmp_path / "f.json"))
    st.run(ctx)
    assert (tmp_path / "tables" / "demo.tex").is_file()
    assert (tmp_path / "tables-pt" / "demo.tex").is_file()
    assert ctx.cache["results_summary"]["latex_tables"] == 2


def test_an_empty_latex_table_aborts_rather_than_shipping(tmp_path, monkeypatch):
    class _Empty:
        TABLES = {"demo": lambda f: "   "}

    def _load(name):
        if name == "results_figures":
            return _FakeRF(3)
        if name == "gen_tables_tex":
            return _Empty()
        return _FakeGR()

    _patch(monkeypatch, _load)
    with pytest.raises(RuntimeError, match="rendered empty"):
        st.run(_ctx(tmp_path, doc=str(_doc(tmp_path, ["a"])), figures=str(tmp_path / "f.json")))


def test_catalogue_has_no_null_columns():
    f = {"catalogue_sample": {"rows": [{
        "name": "Tipo X", "n_cases": 10, "n_evaluated": 9, "top1": 0.8,
        "unit_recall": 0.9, "visits_in_path": None, "unseen_per_visit": None}],
        "note": ""}}
    body = ctab.t_catalogue(f)
    assert "---" not in body
    assert "visits" not in body and "unseen/visit" not in body


def test_delta_star_drops_coverage_column_when_all_none():
    fam = {"per_cluster_top1": 0.7, "shuffled_top1": 0.5, "delta_star_top1": 0.2,
           "delta_star_adjusted": 0.19, "delta_star_coverage_fidelity": None}
    f = {"controls": {"procedure": {"per_family_like_for_like": {"markov": fam}}}}
    body = ttab.t_delta_star(f)
    assert "$\\Delta^{*}$ coverage \\\\" not in body and "---" not in body


def test_delta_star_keeps_coverage_column_when_present():
    fam = {"per_cluster_top1": 0.7, "shuffled_top1": 0.5, "delta_star_top1": 0.2,
           "delta_star_adjusted": 0.19, "delta_star_coverage_fidelity": 0.3}
    f = {"controls": {"unit": {"per_family_like_for_like": {"markov": fam}}}}
    body = ttab.t_delta_star(f)
    assert "$\\Delta^{*}$ coverage \\\\" in body


def test_intrinsic_drops_constant_rows_and_labels_refused():
    f = {"intrinsic_vs_downstream": {"permutation": {
        "noise_ratio": {"rho": None, "p_permutation": None},
        "noise_ratio_refused": {"rho": -0.055, "p_permutation": 0.853}},
        "n_clusterings": 14, "n_permutations": 20000,
        "downstream_spread": 0.112, "downstream_relative_spread": 0.34}}
    body = ctab.t_intrinsic(f)
    assert "noise_ratio_refused" not in body and "ratio\\_refused" not in body
    assert "---" not in body
