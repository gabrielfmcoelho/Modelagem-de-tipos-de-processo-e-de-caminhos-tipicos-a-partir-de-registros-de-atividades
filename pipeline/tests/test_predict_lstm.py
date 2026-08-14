
from __future__ import annotations

import pytest

_VALID = ["GERACAO-PROCEDIMENTO@U1", "PROCESSO-REMETIDO-UNIDADE@U2",
          "PROCESSO-RECEBIDO-UNIDADE@U2", "CONCLUSAO-PROCESSO-UNIDADE@U2", "<END>"]


def test_lstm_aux_loss_and_rl_finetune_run():
    pytest.importorskip("torch")
    from ..model.predict_lstm import LSTMModel

    m = LSTMModel(epochs=3, hidden=16, embed=8, aux_lambda=1.5).fit([list(_VALID)] * 24)
    assert m.available
    nxt = m.predict_next(["GERACAO-PROCEDIMENTO@U1"], topk=1)
    assert isinstance(nxt, list) and nxt

    m.fit_rl(["GERACAO-PROCEDIMENTO@U1"], rl_epochs=2, rl_batch=4, max_steps=8)
    assert m.available


def test_true_lstm_fits_and_predicts():
    pytest.importorskip("torch")
    from ..model.predict_lstm import TrueLSTMModel

    m = TrueLSTMModel(epochs=3, hidden=16, embed=8).fit([list(_VALID)] * 24)
    assert m.available
    nxt = m.predict_next(["GERACAO-PROCEDIMENTO@U1"], topk=1)
    assert isinstance(nxt, list) and nxt
