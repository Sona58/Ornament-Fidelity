"""f0 -> tonic-relative cents on a uniform 10 ms grid, split into voiced runs."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter

HOP_S = 0.01  # uniform analysis grid (10 ms), as in the manuscript


def to_cents_grid(t: np.ndarray, f0: np.ndarray, tonic_hz: float,
                  hop: float = HOP_S, max_gap_s: float = 0.05):
    """Resample to a uniform grid in tonic-relative cents. Gaps longer than
    `max_gap_s` (unvoiced / dropouts) stay NaN. Returns (t_grid, cents)."""
    voiced = np.isfinite(f0) & (f0 > 40) & (f0 < 2000)
    tv, fv = t[voiced], f0[voiced]
    if tv.size < 10:
        return np.array([]), np.array([])
    native = float(np.median(np.diff(tv))) if tv.size > 1 else hop
    tg = np.arange(tv[0], tv[-1], hop)
    cents_v = 1200.0 * np.log2(fv / tonic_hz)
    c = np.interp(tg, tv, cents_v)
    idx = np.clip(np.searchsorted(tv, tg), 1, tv.size - 1)
    left, right = tv[idx - 1], tv[idx]
    gap = right - left
    dist = np.minimum(tg - left, right - tg)
    ok = (gap <= max(max_gap_s, 2.5 * native)) | (dist <= 1.5 * native)
    c[~ok] = np.nan
    return tg, c


def voiced_runs(c: np.ndarray, min_len: int = 45, jump_cents: float = 300.0):
    """Split at NaNs and at implausible frame-to-frame jumps (octave errors).
    Returns list of (i0, i1_exclusive)."""
    n = c.size
    valid = np.isfinite(c)
    jumps = np.zeros(n, dtype=bool)
    d = np.abs(np.diff(c, prepend=c[0]))
    jumps[1:] = np.nan_to_num(d[1:], nan=0.0) > jump_cents
    runs, start = [], None
    for i in range(n):
        if valid[i] and not jumps[i]:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= min_len:
                runs.append((start, i))
            start = i if (valid[i] and jumps[i]) else None
    if start is not None and n - start >= min_len:
        runs.append((start, n))
    return runs


def clean_run(c_run: np.ndarray, kernel: int = 5) -> np.ndarray:
    """5-frame (50 ms) median filter: the *reference contour* all models are scored against."""
    return median_filter(c_run, size=kernel, mode="nearest")
