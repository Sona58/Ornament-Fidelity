"""Heuristic detection of meend-like glides and andolan-like oscillations.

IMPORTANT: these are signal-based proxies, NOT ground-truth ornament labels
(ROD annotations are not used). Thresholds follow the duration constraints of
the ROD taxonomy (meend >= 0.45 s; andolan >= 1.0 s, here a stricter 2.0 s
window so that frequency can be estimated). Use `audit_sheet.csv` to estimate
detection precision by hand before reporting results.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from scipy.signal import savgol_filter

DT = 0.01


@dataclass
class GlideParams:
    min_slope: float = 100.0      # cents/s
    merge_gap: int = 5            # frames
    min_dur: float = 0.45         # s  (ROD meend)
    max_dur: float = 4.0          # s
    min_excursion: float = 100.0  # cents
    min_straightness: float = 0.85  # |net| / path length
    extend_slope: float = 20.0    # cents/s: grow boundaries outward into the flat shoulders
    max_extend: int = 40          # frames (0.4 s) per side


@dataclass
class OscParams:
    window: float = 2.0           # s
    hop: float = 0.25             # s
    f_lo: float = 1.0             # Hz
    f_hi: float = 6.5             # Hz
    amp_lo: float = 15.0          # cents (sinusoid amplitude estimate)
    amp_hi: float = 150.0
    max_trend: float = 100.0      # cents drift across window
    min_peak_frac: float = 0.5    # spectral concentration
    max_dev_ratio: float = 3.0    # reject windows with jumps/glides: max|resid| / std(resid)
    edge_margin: float = 0.0      # Hz: spectral peak must lie at least this far inside [f_lo, f_hi]
    require_dominant: bool = False  # no stronger spectral component between 0.3 Hz and f_lo (slow wander)


# Presets. "strict-osc" narrows the oscillation detector toward slow, regular, moderate-amplitude
# oscillations (andolan) and away from fast vibrato-like or jumpy contours.
OSC_PRESETS = {
    "default": OscParams(),
    "strict-osc": OscParams(f_hi=4.5, amp_lo=25.0, amp_hi=100.0, min_peak_frac=0.7, max_dev_ratio=2.5),
    # v0.5: audit showed most false positives had their spectral peak pinned at the 1 Hz band edge.
    "interior-osc": OscParams(f_hi=4.5, amp_lo=25.0, amp_hi=100.0, min_peak_frac=0.7, max_dev_ratio=2.5,
                              edge_margin=0.15, require_dominant=True),
    # v0.5.1: keeps the original thresholds and 1-6.5 Hz band (audited 'Yes' labels included 4-6 Hz oscillations)
    # and removes only the band-edge artifact. Pooled audits: interior peaks 15/18 genuine vs edge peaks 15/35.
    "interior-wide": OscParams(edge_margin=0.15, require_dominant=True),
    # v0.6: slow, wide oscillation about one pitch (andolan). Audit of 'interior-wide': <=3 Hz 20/22 genuine andolan,
    # >3 Hz 3/17 (the rest were thin, fast kampit/gamak-like waves). The 3 Hz cut was chosen from that audit, so it must
    # be confirmed on a fresh audit sample before being treated as validated.
    "andolan": OscParams(f_hi=3.15, edge_margin=0.15, require_dominant=True),
    # longer windows resolve slower oscillations (0.5-3 Hz) that a 2 s window cannot separate from drift.
    "slow-osc": OscParams(window=4.0, hop=0.5, f_lo=0.5, f_hi=3.0, amp_lo=25.0, amp_hi=100.0,
                          min_peak_frac=0.6, max_dev_ratio=2.5, edge_margin=0.1, require_dominant=True),
}


def params_dict():
    return {"glide": asdict(GlideParams()), "osc": asdict(OscParams())}


def detect_glides(c: np.ndarray, p: GlideParams = GlideParams()):
    """c: cleaned contour of one voiced run. Returns list of dicts with i0,i1 (inclusive)."""
    n = c.size
    if n < 21:
        return []
    sm = savgol_filter(c, 11, 2)
    slope = np.gradient(sm, DT)
    sign = np.where(np.abs(slope) >= p.min_slope, np.sign(slope), 0).astype(int)
    segs, i = [], 0
    while i < n:
        if sign[i] == 0:
            i += 1
            continue
        s, j, last = sign[i], i, i
        while j < n:
            if sign[j] == s:
                last = j
            elif sign[j] == -s or (j - last) > p.merge_gap:
                break
            j += 1
        segs.append((i, last))
        i = last + 1
    out = []
    for i0, i1 in segs:
        s_dir = np.sign(sm[i1] - sm[i0])
        for _ in range(p.max_extend):          # extend into low-slope shoulders, same direction only
            if i0 > 0 and s_dir * slope[i0 - 1] >= p.extend_slope:
                i0 -= 1
            else:
                break
        for _ in range(p.max_extend):
            if i1 < n - 1 and s_dir * slope[i1 + 1] >= p.extend_slope:
                i1 += 1
            else:
                break
        dur = (i1 - i0 + 1) * DT
        if not (p.min_dur <= dur <= p.max_dur):
            continue
        net = sm[i1] - sm[i0]
        path = np.sum(np.abs(np.diff(sm[i0:i1 + 1])))
        if abs(net) < p.min_excursion or path <= 0:
            continue
        straight = abs(net) / path
        if straight < p.min_straightness:
            continue
        out.append(dict(i0=i0, i1=i1, duration=dur, excursion=float(net), straightness=float(straight)))
    return out


def detect_oscillations(c: np.ndarray, p: OscParams = OscParams()):
    W, H = int(round(p.window / DT)), int(round(p.hop / DT))
    n = c.size
    out, start = [], 0
    hann = np.hanning(W)
    nfft = 2048
    freqs = np.fft.rfftfreq(nfft, DT)
    t = np.arange(W) * DT
    while start + W <= n:
        seg = c[start:start + W]
        coef = np.polyfit(t, seg, 1)
        trend = abs(coef[0] * p.window)
        x = seg - np.polyval(coef, t)
        amp = np.sqrt(2.0) * np.std(x)
        sd = np.std(x)
        ok = (trend <= p.max_trend) and (p.amp_lo <= amp <= p.amp_hi) and sd > 0 \
            and (np.max(np.abs(x)) / sd <= p.max_dev_ratio)
        if ok:
            pw = np.abs(np.fft.rfft(x * hann, nfft)) ** 2
            band = (freqs >= p.f_lo) & (freqs <= p.f_hi)
            k = np.argmax(np.where(band, pw, 0))
            f_pk = freqs[k]
            if p.edge_margin > 0 and not (p.f_lo + p.edge_margin <= f_pk <= p.f_hi - p.edge_margin):
                ok = False          # peak pinned to the band edge: true power lies outside the band
            if ok and p.require_dominant:
                low = (freqs >= 0.3) & (freqs < p.f_lo)
                if low.any() and pw[low].max() > pw[k]:
                    ok = False      # slow wander / drift dominates the window
            near = (freqs >= f_pk - 0.5) & (freqs <= f_pk + 0.5)
            total = pw[freqs >= 0.3].sum()
            frac = pw[near].sum() / total if total > 0 else 0.0
            ok = ok and (frac >= p.min_peak_frac)
        if ok:
            out.append(dict(i0=start, i1=start + W - 1, duration=p.window,
                            freq_hz=float(f_pk), amp_cents=float(amp), peak_frac=float(frac)))
            start += W
        else:
            start += H
    return out
