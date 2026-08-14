from __future__ import annotations

from .._torch_base import PAD, _TorchSeqModel


class TrueLSTMModel(_TorchSeqModel):

    def _build_net(self, V, nn):
        E, H, drop = self.embed, self.hidden, self.dropout

        class _Net(nn.Module):
            def __init__(s):
                super().__init__()
                s.emb = nn.Embedding(V, E, padding_idx=PAD)
                s.lstm = nn.LSTM(E, H, batch_first=True)
                s.drop = nn.Dropout(drop)
                s.fc = nn.Linear(H, V)

            def forward(s, x):
                _, (h, _) = s.lstm(s.emb(x))
                return s.fc(s.drop(h[-1]))

        return _Net()
