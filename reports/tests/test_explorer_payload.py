import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import gen_14_explorer as g

FIX = json.loads((Path(__file__).parent / "fixtures" / "sample_payload.json").read_text())


def test_timelines_for_entry_groups_and_encodes_sequences():
    entry = FIX["combos"][0]["clusters"][0]["eval"]
    vocab = {}

    def enc(states):
        return [vocab.setdefault(s, len(vocab)) for s in states]

    tl = g.timelines_for_entry(entry, ["GERACAO-PROCEDIMENTO@A", "CONCLUSAO-PROCESSO-UNIDADE@A"],
                               ["GERACAO-PROCEDIMENTO@A", "CONCLUSAO-PROCESSO-UNIDADE@A"], enc)
    kinds = {t["kind"] for t in tl}
    assert {"observado", "classico"} <= kinds
    for t in tl:
        assert isinstance(t["seq"], list) and t["seq"] and all(isinstance(i, int) for i in t["seq"])
    assert vocab["GERACAO-PROCEDIMENTO@A"] == 0
    assert len(vocab) >= 2


def test_render_html_is_selfcontained_and_has_markers():
    html = g.render_html(FIX)
    body = html.replace("http://www.w3.org/2000/svg", "")
    assert "http://" not in body and "https://" not in body.split("<title>")[0]
    assert "Retirada de Descontos" in html
    assert "application/json" in html
