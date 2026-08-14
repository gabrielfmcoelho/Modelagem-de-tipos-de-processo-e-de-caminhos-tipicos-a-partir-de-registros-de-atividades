
from __future__ import annotations

import pytest

_VALID = ["GERACAO-PROCEDIMENTO@U1", "PROCESSO-REMETIDO-UNIDADE@U2",
          "PROCESSO-RECEBIDO-UNIDADE@U2", "CONCLUSAO-PROCESSO-UNIDADE@U2", "<END>"]


def test_transformer_fits_predicts_and_generates():
    pytest.importorskip("torch")
    from ..model.predict_lstm import TransformerModel

    m = TransformerModel(epochs=4, embed=16, hidden=32, heads=2, layers=1, window=8).fit([list(_VALID)] * 24)
    assert m.available
    nxt = m.predict_next(["GERACAO-PROCEDIMENTO@U1"], topk=1)
    assert isinstance(nxt, list) and nxt
    seq = m.generate("GERACAO-PROCEDIMENTO@U1", is_conclusion=lambda s: s == "<END>", max_steps=10)
    assert seq[0] == "GERACAO-PROCEDIMENTO@U1"
    dist = m.next_distribution(["GERACAO-PROCEDIMENTO@U1"])
    assert dist and all(isinstance(s, str) for s, _ in dist)


def test_transformer_aux_loss_runs():
    pytest.importorskip("torch")
    from ..model.predict_lstm import TransformerModel

    m = TransformerModel(epochs=3, embed=16, hidden=32, heads=2, layers=1, aux_lambda=1.0).fit([list(_VALID)] * 24)
    assert m.available
