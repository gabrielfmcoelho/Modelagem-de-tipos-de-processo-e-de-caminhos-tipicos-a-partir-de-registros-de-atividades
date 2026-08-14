from __future__ import annotations

from .dfg.dfg_model import DfgModel
from .gru.gru_model import LSTMModel as GruModel
from .lstm.lstm_model import TrueLSTMModel as LstmModel
from .markov.markov_model import MarkovModel
from .transformer.transformer_model import TransformerModel

MODEL_NAMES = ("markov", "dfg", "gnn", "gru", "lstm", "transformer")

__all__ = ["MODEL_NAMES", "MarkovModel", "DfgModel", "GruModel", "LstmModel",
           "TransformerModel"]
