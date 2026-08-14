import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from explorer_content import ALGORITHMS, GLOSSARY, PIPELINE_STAGES

REQUIRED_GLOSSARY = {"top1", "top3", "suffix_dl", "suffix_length_ratio",
                     "flow_validity_step", "flow_validity_trace",
                     "typical_path_distance", "typical_path_distance_proc",
                     "medoid_distance", "dispersion",
                     "edge_coverage", "edge_usage", "edge_f1", "keywords",
                     "dbcv", "silhouette", "purity", "nmi", "ari", "handoffs"}
MODEL_KEYS = {"real", "comum", "markov", "dfg", "gru", "lstm", "transformer"}


def test_glossary_has_all_indicators_with_text():
    assert REQUIRED_GLOSSARY <= set(GLOSSARY)
    for k, v in GLOSSARY.items():
        assert v["label"] and v["short"] and v["long"]


def test_algorithms_cover_every_timeline_lane():
    keys = {a["key"] for a in ALGORITHMS}
    assert MODEL_KEYS <= keys
    for a in ALGORITHMS:
        assert a["kind"] in {"observado", "classico", "neural", "clustering", "support"}
        assert a["name"] and a["manipulation"]


def test_pipeline_stages_nonempty():
    assert len(PIPELINE_STAGES) >= 6
    for s in PIPELINE_STAGES:
        assert s["stage"] and s["does"]
