# -*- coding: utf-8 -*-
"""FableDan Q-network (PyTorch): tiny Llama-style causal encoder over the
game-history token stream + hand/action MLP + Q head (+ optional NTP head).

Weight names are kept stable so export_npz()/model_np.py can mirror them.
"""

import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .encode import FEAT_DIM, MAX_SEQ, PAD_TOK, VOCAB


class ModelConfig:
    def __init__(self, d_model=128, n_blocks=4, n_heads=4, qk_dim=64,
                 v_dim=64, ffn_hidden=512, hand_hidden=512, n_hand_layers=3,
                 q_hidden=1024, n_q_layers=3, max_seq=MAX_SEQ,
                 ntp_weight=0.02, vocab=VOCAB, feat_dim=FEAT_DIM):
        self.d_model = d_model
        self.n_blocks = n_blocks
        self.n_heads = n_heads
        self.qk_dim = qk_dim
        self.v_dim = v_dim
        self.ffn_hidden = ffn_hidden
        self.hand_hidden = hand_hidden
        self.n_hand_layers = n_hand_layers
        self.q_hidden = q_hidden
        self.n_q_layers = n_q_layers
        self.max_seq = max_seq
        self.ntp_weight = ntp_weight
        self.vocab = vocab
        self.feat_dim = feat_dim

    def to_dict(self):
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d):
        c = cls()
        for k, v in d.items():
            if hasattr(c, k):
                setattr(c, k, v)
        return c


class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x):
        var = x.float().pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(var + self.eps).to(x.dtype)
        return x * self.weight


def build_rope(max_seq, dim, theta=10000.0):
    half = dim // 2
    freqs = 1.0 / (theta ** (torch.arange(0, half).float() / half))
    t = torch.arange(max_seq).float()
    ang = torch.outer(t, freqs)
    return torch.cos(ang), torch.sin(ang)


def apply_rope(x, cos, sin):
    # x: [B, H, T, D]; cos/sin: [T, D/2]
    d = x.shape[-1] // 2
    x1, x2 = x[..., :d], x[..., d:]
    c = cos[None, None, :x.shape[2], :]
    s = sin[None, None, :x.shape[2], :]
    return torch.cat([x1 * c - x2 * s, x1 * s + x2 * c], dim=-1)


class Attention(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        h, qk, v = cfg.n_heads, cfg.qk_dim, cfg.v_dim
        self.h, self.qk, self.v = h, qk, v
        self.q_proj = nn.Linear(cfg.d_model, h * qk, bias=False)
        self.k_proj = nn.Linear(cfg.d_model, h * qk, bias=False)
        self.v_proj = nn.Linear(cfg.d_model, h * v, bias=False)
        self.out_proj = nn.Linear(h * v, cfg.d_model, bias=False)
        self.q_norm = RMSNorm(qk)
        self.k_norm = RMSNorm(qk)

    def forward(self, x, cos, sin, attn_mask=None):
        B, T, _ = x.shape
        q = self.q_proj(x).view(B, T, self.h, self.qk).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.h, self.qk).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.h, self.v).transpose(1, 2)
        q = apply_rope(self.q_norm(q), cos, sin)
        k = apply_rope(self.k_norm(k), cos, sin)
        # pure causal attention -> flash-attention kernel, O(T) memory.
        # PAD tokens sit at the tail of each sequence, so causal masking
        # already keeps them out of every real position's receptive field.
        o = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        o = o.transpose(1, 2).reshape(B, T, self.h * self.v)
        return self.out_proj(o)


class FFN(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.gate_proj = nn.Linear(cfg.d_model, cfg.ffn_hidden, bias=False)
        self.up_proj = nn.Linear(cfg.d_model, cfg.ffn_hidden, bias=False)
        self.down_proj = nn.Linear(cfg.ffn_hidden, cfg.d_model, bias=False)

    def forward(self, x):
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class Block(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.attn_norm = RMSNorm(cfg.d_model)
        self.attn = Attention(cfg)
        self.ffn_norm = RMSNorm(cfg.d_model)
        self.ffn = FFN(cfg)

    def forward(self, x, cos, sin, mask=None):
        x = x + self.attn(self.attn_norm(x), cos, sin, mask)
        x = x + self.ffn(self.ffn_norm(x))
        return x


def _mlp(in_dim, hidden, n_hidden, out_dim):
    layers = [nn.Linear(in_dim, hidden), nn.ReLU()]
    for _ in range(n_hidden - 1):
        layers += [nn.Linear(hidden, hidden), nn.ReLU()]
    layers.append(nn.Linear(hidden, out_dim))
    return nn.Sequential(*layers)


class FableDanNet(nn.Module):
    def __init__(self, cfg=None):
        super().__init__()
        self.cfg = cfg or ModelConfig()
        cfg = self.cfg
        self.token_emb = nn.Embedding(cfg.vocab, cfg.d_model)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_blocks))
        self.final_norm = RMSNorm(cfg.d_model)
        cos, sin = build_rope(cfg.max_seq, cfg.qk_dim)
        self.register_buffer("rope_cos", cos, persistent=True)
        self.register_buffer("rope_sin", sin, persistent=True)
        self.hand_mlp = _mlp(cfg.feat_dim, cfg.hand_hidden,
                             cfg.n_hand_layers, cfg.d_model)
        self.q_head = _mlp(cfg.d_model * 2, cfg.q_hidden, cfg.n_q_layers, 1)
        self.ntp_head = nn.Linear(cfg.d_model, cfg.vocab, bias=False)
        # belief head: predict the 3 opponents'/partner's hidden hand
        # rank-count vectors (3 x 15, /4 normalized) from the context.
        # Training-only auxiliary (oracle labels); not used at inference.
        self.belief_head = nn.Sequential(
            nn.Linear(cfg.d_model, 256), nn.ReLU(), nn.Linear(256, 45))

    def encode_seq(self, tokens, lengths):
        """tokens: [B, T] int64 (PAD=0); lengths: [B]. -> ctx [B, d], hid [B,T,d]"""
        B, T = tokens.shape
        x = self.token_emb(tokens)
        cos = self.rope_cos.to(x.dtype)
        sin = self.rope_sin.to(x.dtype)
        for blk in self.blocks:
            x = blk(x, cos, sin)
        x = self.final_norm(x)
        idx = (lengths - 1).clamp(min=0)
        ctx = x[torch.arange(B, device=x.device), idx]
        return ctx, x

    def q_values(self, ctx, feats):
        """ctx: [B, d]; feats: [B, A, F] -> [B, A]"""
        hemb = self.hand_mlp(feats)
        c = ctx[:, None, :].expand(-1, feats.shape[1], -1)
        q = self.q_head(torch.cat([c, hemb], dim=-1))
        return q.squeeze(-1)

    def forward(self, tokens, lengths, feats):
        ctx, hid = self.encode_seq(tokens, lengths)
        return self.q_values(ctx, feats), hid

    def belief_loss(self, ctx, belief_labels):
        """MSE between predicted and oracle hidden-hand count vectors."""
        pred = self.belief_head(ctx)
        return F.mse_loss(pred, belief_labels)

    def ntp_loss(self, tokens, hid):
        """next-token prediction over non-pad positions."""
        logits = self.ntp_head(hid[:, :-1])
        targets = tokens[:, 1:]
        mask = targets != PAD_TOK
        if mask.sum() == 0:
            return torch.zeros((), device=tokens.device)
        loss = F.cross_entropy(logits[mask], targets[mask])
        return loss


# ---------------------------------------------------------------------------

def export_npz(model, path):
    """Save weights + config to .npz for numpy inference / botzone."""
    sd = model.state_dict()
    arrays = {k: v.detach().cpu().float().numpy() for k, v in sd.items()
              if not k.startswith(("ntp_head", "belief_head"))}
    cfg = model.cfg.to_dict()
    arrays["__config__"] = np.array(
        [f"{k}={v}" for k, v in cfg.items()], dtype=np.str_)
    np.savez_compressed(path, **arrays)


def save_ckpt(model, optimizer, meta, path):
    torch.save({"model": model.state_dict(),
                "optimizer": optimizer.state_dict() if optimizer else None,
                "config": model.cfg.to_dict(),
                "meta": meta}, path)


def load_ckpt(path, device="cpu"):
    ck = torch.load(path, map_location=device, weights_only=False)
    cfg = ModelConfig.from_dict(ck["config"])
    model = FableDanNet(cfg).to(device)
    model.load_state_dict(ck["model"])
    return model, ck
