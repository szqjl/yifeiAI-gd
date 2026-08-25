# -*- coding: utf-8 -*-
"""Pure-numpy inference of FableDanNet (for Botzone deployment & sandbox).

Loads the .npz produced by model_torch.export_npz. Single-sequence forward.

Memory: uses float32 throughout (no float64 upcast) to stay under Botzone's
256 MB sandbox limit.  Peak allocation ~20 MB for a 512-token sequence with
~100 legal moves.
"""

import gc

import numpy as np


def _rms(x, w, eps=1e-6):
    """RMS norm in float32 (avoid float64 to reduce memory on constrained sandbox)."""
    v = np.mean(x.astype(np.float32) ** 2, axis=-1, keepdims=True)
    return (x / np.sqrt(v + eps)) * w


def _silu(x):
    return x / (1.0 + np.exp(-x))


def _relu(x):
    return np.maximum(x, 0.0)


def _softmax(x, axis=-1):
    m = x.max(axis=axis, keepdims=True)
    e = np.exp(x - m)
    return e / e.sum(axis=axis, keepdims=True)


class NumpyModel:
    def __init__(self, npz_path_or_dict):
        if isinstance(npz_path_or_dict, dict):
            w = npz_path_or_dict
        else:
            w = dict(np.load(npz_path_or_dict, allow_pickle=False))
        self.w = {k: v for k, v in w.items() if k != "__config__"}
        cfg = {}
        if "__config__" in w:
            for item in w["__config__"]:
                k, _, v = str(item).partition("=")
                try:
                    cfg[k] = int(v)
                except ValueError:
                    try:
                        cfg[k] = float(v)
                    except ValueError:
                        cfg[k] = v
        self.cfg = cfg
        self.n_blocks = int(cfg.get("n_blocks", 4))
        self.n_heads = int(cfg.get("n_heads", 4))
        self.qk = int(cfg.get("qk_dim", 64))
        self.v = int(cfg.get("v_dim", 64))
        self.rope_cos = self.w["rope_cos"]
        self.rope_sin = self.w["rope_sin"]

    # ------------------------------------------------------------------
    def _attn(self, x, i):
        w = self.w
        T = x.shape[0]
        h, qk, vd = self.n_heads, self.qk, self.v
        pre = "blocks.%d.attn." % i
        q = x @ w[pre + "q_proj.weight"].T
        k = x @ w[pre + "k_proj.weight"].T
        v = x @ w[pre + "v_proj.weight"].T
        q = q.reshape(T, h, qk).transpose(1, 0, 2)
        k = k.reshape(T, h, qk).transpose(1, 0, 2)
        v = v.reshape(T, h, vd).transpose(1, 0, 2)
        q = _rms(q, w[pre + "q_norm.weight"])
        k = _rms(k, w[pre + "k_norm.weight"])
        q = self._rope(q, T)
        k = self._rope(k, T)
        scores = q @ k.transpose(0, 2, 1) / np.sqrt(qk)
        mask = np.triu(np.full((T, T), -1e30, dtype=np.float32), k=1)
        scores = scores + mask[None]
        a = _softmax(scores, axis=-1)
        o = a @ v                       # [h, T, vd]
        o = o.transpose(1, 0, 2).reshape(T, h * vd)
        return o @ w[pre + "out_proj.weight"].T

    def _rope(self, x, T):
        d = x.shape[-1] // 2
        c = self.rope_cos[:T][None]
        s = self.rope_sin[:T][None]
        x1, x2 = x[..., :d], x[..., d:]
        return np.concatenate([x1 * c - x2 * s, x1 * s + x2 * c], axis=-1)

    def _mlp(self, x, prefix, n_layers):
        w = self.w
        # Sequential indices 0,2,4,... are Linear layers
        idxs = [k for k in w if k.startswith(prefix) and k.endswith(".weight")]
        order = sorted(int(k[len(prefix):].split(".")[0]) for k in idxs)
        for j, li in enumerate(order):
            x = x @ w["%s%d.weight" % (prefix, li)].T + w["%s%d.bias" % (prefix, li)]
            if j < len(order) - 1:
                x = _relu(x)
        return x

    # ------------------------------------------------------------------
    def context(self, tokens):
        """tokens: list[int] -> ctx vector [d]."""
        w = self.w
        x = w["token_emb.weight"][np.asarray(tokens, dtype=np.int64)]
        for i in range(self.n_blocks):
            pre = "blocks.%d." % i
            x = x + self._attn(_rms(x, w[pre + "attn_norm.weight"]), i)
            h = _rms(x, w[pre + "ffn_norm.weight"])
            g = h @ w[pre + "ffn.gate_proj.weight"].T
            u = h @ w[pre + "ffn.up_proj.weight"].T
            x = x + (_silu(g) * u) @ w[pre + "ffn.down_proj.weight"].T
        x = _rms(x, w["final_norm.weight"])
        # Free attention intermediates accumulated over blocks
        gc.collect()
        return x[-1]

    def q_values(self, tokens, feats):
        """feats: [A, FEAT_DIM] -> q: [A]"""
        try:
            ctx = self.context(tokens)
            hemb = self._mlp(np.asarray(feats, dtype=np.float32), "hand_mlp.", None)
            c = np.broadcast_to(ctx, (hemb.shape[0], ctx.shape[0]))
            q = self._mlp(np.concatenate([c, hemb], axis=-1), "q_head.", None)
            return q[:, 0]
        finally:
            gc.collect()
