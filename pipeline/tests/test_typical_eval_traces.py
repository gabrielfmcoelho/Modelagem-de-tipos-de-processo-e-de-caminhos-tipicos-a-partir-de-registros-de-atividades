from ..model.predict import MarkovModel
from ..model.typical_eval import DfgModel, ModelSpec, evaluate_cluster

G = "GERACAO-PROCEDIMENTO@SEAD/A"
R = "REMETIDO-PROCESSO-UNIDADE@SEAD/A"
C = "RECEBIDO-PROCESSO-UNIDADE@SEAD/B"
F = "CONCLUSAO-PROCESSO-UNIDADE@SEAD/B"


def _traces():
    base = [G, R, C, F]
    return [(f"2025-01-{i:02d}", list(base)) for i in range(1, 13)]


def _specs():
    return [ModelSpec("markov", lambda: MarkovModel(3)), ModelSpec("dfg", DfgModel)]


def test_emit_traces_adds_per_model_and_cluster_traces():
    res = evaluate_cluster(_traces(), _specs(), emit_traces=True)
    assert res is not None
    for name in ("markov", "dfg"):
        assert isinstance(res["models"][name]["trace"], list)
        assert len(res["models"][name]["trace"]) >= 1
    assert len(res["real"]) >= 1
    assert len(res["comum"]) >= 1


def test_no_emit_keeps_metrics_only():
    res = evaluate_cluster(_traces(), _specs(), emit_traces=False)
    assert "trace" not in res["models"]["markov"]
    assert "real" not in res and "comum" not in res
