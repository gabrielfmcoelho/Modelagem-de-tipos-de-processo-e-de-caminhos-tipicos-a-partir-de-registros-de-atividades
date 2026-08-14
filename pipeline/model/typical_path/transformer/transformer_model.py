from __future__ import annotations

from .._torch_base import PAD, _TorchSeqModel


class TransformerModel(_TorchSeqModel):

    def __init__(self, *, heads: int = 4, layers: int = 2, **kw):
        super().__init__(**kw)
        self.heads, self.layers = heads, layers

    def _build_net(self, V, nn):
        import torch
        E, H, drop, window, heads, layers = (self.embed, self.hidden, self.dropout,
                                             self.window, self.heads, self.layers)

        class _Net(nn.Module):
            def __init__(s):
                super().__init__()
                s.emb = nn.Embedding(V, E, padding_idx=PAD)
                s.pos = nn.Embedding(window, E)
                layer = nn.TransformerEncoderLayer(E, heads, dim_feedforward=H, dropout=drop,
                                                   batch_first=True)
                s.enc = nn.TransformerEncoder(layer, layers)
                s.fc = nn.Linear(E, V)

            def forward(s, x):
                T = x.size(1)
                pos = torch.arange(T, device=x.device)
                h = s.emb(x) + s.pos(pos)[None, :, :]
                pad = (x == PAD)
                h = s.enc(h, src_key_padding_mask=pad)
                return s.fc(h[:, -1])

        return _Net()
