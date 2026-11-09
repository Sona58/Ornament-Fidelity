"""Tiny additive synthesiser: render a tonic-relative cents contour as a harmonic tone.
The same timbre is used for every variant so listeners compare *contour* only."""
from __future__ import annotations

import numpy as np
from scipy.io import wavfile

SR = 22050


def synth(cents: np.ndarray, tonic_hz: float, dt: float = 0.01, sr: int = SR,
          n_harm: int = 8, pad_s: float = 0.25, fade_s: float = 0.03) -> np.ndarray:
    pad = int(round(pad_s / dt))
    c = np.concatenate([np.full(pad, cents[0]), cents, np.full(pad, cents[-1])])
    t_ctrl = np.arange(len(c)) * dt
    n = int(len(c) * dt * sr)
    t = np.arange(n) / sr
    f = tonic_hz * 2 ** (np.interp(t, t_ctrl, c) / 1200.0)
    phase = 2 * np.pi * np.cumsum(f) / sr
    y = sum((1.0 / k) * np.sin(k * phase) for k in range(1, n_harm + 1) if k * f.max() < sr / 2)
    nf = int(fade_s * sr)
    env = np.ones(n)
    env[:nf] = np.linspace(0, 1, nf)
    env[-nf:] = np.linspace(1, 0, nf)
    y = y * env
    return (0.5 * y / np.max(np.abs(y))).astype(np.float32)


def write_wav(path, y: np.ndarray, sr: int = SR):
    wavfile.write(str(path), sr, (np.clip(y, -1, 1) * 32767).astype(np.int16))


def concat_with_gaps(waves, gap_s: float = 0.4, sr: int = SR):
    gap = np.zeros(int(gap_s * sr), dtype=np.float32)
    parts = []
    for w in waves:
        parts += [w, gap]
    return np.concatenate(parts[:-1])
