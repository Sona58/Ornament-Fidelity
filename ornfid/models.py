"""Candidate representations of one ornament segment (all in tonic-relative cents).

Glide (meend-like):
  tet12_notes     two held 12-TET notes (start/end snapped), switch at midpoint  [MIDI-style]
  shruti22_notes  same, snapped to a 22-shruti just-intonation grid
  tet12_framesnap frame-wise 12-TET snapping of the contour (lower bound on grid error)
  linear          straight-line glide (2 free parameters)
  cosine_module1  cosine-eased glide over the whole segment = expectation trajectory of a
                  CV displacement with a cosine path (original Module 1; 2 parameters)
  plateau_ramp    hold - linear ramp - hold (4 parameters: a, b, onset, offset)
  plateau_cosine  hold - cosine ramp - hold (4 parameters) = CV displacement whose path
                  alpha(t) has fitted onset/offset ("Module 1+")

Oscillation (andolan-like):
  tet12_note      single held 12-TET note (median pitch snapped)
  shruti22_note   single held 22-shruti note
  tet12_framesnap frame-wise 12-TET snapping of the contour
  steady_free     single held note at the *unquantised* mean (1 parameter)
  linear_drift    straight line (2 parameters): is the "oscillation" just drift?
  sinusoid_module1  c + A sin(2 pi f t + phi) = CV rotation trajectory (4 parameters)
  sinusoid_drift  sinusoid + linear drift (5 parameters)
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

_SHRUTI_RATIOS = [1, 256/243, 16/15, 10/9, 9/8, 32/27, 6/5, 5/4, 81/64, 4/3, 27/20,
                  45/32, 729/512, 3/2, 128/81, 8/5, 5/3, 27/16, 16/9, 9/5, 15/8, 243/128]
SHRUTI_CENTS = np.array(sorted(1200 * np.log2(_SHRUTI_RATIOS)))
_SHRUTI_GRID = np.array([s + 1200 * k for k in range(-4, 5) for s in SHRUTI_CENTS])
_SHRUTI_GRID.sort()

GLIDE_MODELS = ["tet12_notes", "shruti22_notes", "tet12_framesnap", "linear", "cosine_module1",
                "plateau_ramp", "plateau_cosine"]
OSC_MODELS = ["tet12_note", "shruti22_note", "tet12_framesnap", "steady_free", "linear_drift",
              "sinusoid_module1", "sinusoid_drift"]
# reference models used in paired tests (original Module 1 first, then the extended one)
MODULE1 = {"glide": "cosine_module1", "osc": "sinusoid_module1"}
REFERENCES = {"glide": ["cosine_module1", "plateau_cosine"], "osc": ["sinusoid_module1", "sinusoid_drift"]}
# free continuous parameters (None = non-parametric, excluded from AICc comparisons)
N_PARAMS = {"tet12_notes": 2, "shruti22_notes": 2, "tet12_framesnap": None, "linear": 2,
            "cosine_module1": 2, "plateau_ramp": 4, "plateau_cosine": 4,
            "tet12_note": 1, "shruti22_note": 1, "steady_free": 1, "linear_drift": 2,
            "sinusoid_module1": 4, "sinusoid_drift": 5}
PARAMETRIC = {"glide": ["linear", "cosine_module1", "plateau_ramp", "plateau_cosine"],
              "osc": ["steady_free", "linear_drift", "sinusoid_module1", "sinusoid_drift"]}
PLOT_MODELS = {"glide": ["tet12_notes", "linear", "cosine_module1", "plateau_cosine"],
               "osc": ["tet12_note", "steady_free", "sinusoid_module1", "sinusoid_drift"]}


def snap_12tet(c):
    return np.round(np.asarray(c) / 100.0) * 100.0


def snap_shruti(c):
    c = np.atleast_1d(np.asarray(c, dtype=float))
    idx = np.clip(np.searchsorted(_SHRUTI_GRID, c), 1, _SHRUTI_GRID.size - 1)
    lo, hi = _SHRUTI_GRID[idx - 1], _SHRUTI_GRID[idx]
    return np.where(np.abs(c - lo) <= np.abs(hi - c), lo, hi)


def _ends(y):
    k = max(3, len(y) // 10)
    return float(np.median(y[:k])), float(np.median(y[-k:]))


def _fit_plateau(y, ease):
    """Hold a - ramp(t1..t2) - hold b. Grid over (t1, t2); (a, b) by closed-form least squares."""
    n = len(y)
    u = np.linspace(0.0, 1.0, n)
    t1 = np.linspace(0.0, 0.45, 19)
    t2 = np.linspace(0.55, 1.0, 19)
    T1, T2 = np.meshgrid(t1, t2, indexing="ij")
    T1, T2 = T1.ravel()[:, None], T2.ravel()[:, None]
    phi = np.clip((u[None, :] - T1) / (T2 - T1), 0.0, 1.0)
    if ease == "cos":
        phi = (1 - np.cos(np.pi * phi)) / 2
    w = 1.0 - phi
    s11, s12, s22 = (w * w).sum(1), (w * phi).sum(1), (phi * phi).sum(1)
    r1, r2 = (w * y).sum(1), (phi * y).sum(1)
    det = s11 * s22 - s12 ** 2
    det = np.where(np.abs(det) < 1e-12, 1e-12, det)
    a = (r1 * s22 - r2 * s12) / det
    b = (r2 * s11 - r1 * s12) / det
    pred = a[:, None] * w + b[:, None] * phi
    sse = ((y[None, :] - pred) ** 2).sum(1)
    return pred[int(np.argmin(sse))]


def fit_glide(y: np.ndarray, dt: float = 0.01) -> dict:
    n = len(y)
    u = np.linspace(0.0, 1.0, n)
    a, b = _ends(y)
    first = u < 0.5
    preds = {}
    for name, snap in (("tet12_notes", snap_12tet), ("shruti22_notes", snap_shruti)):
        sa = float(np.atleast_1d(snap(a))[0])
        sb = float(np.atleast_1d(snap(b))[0])
        preds[name] = np.where(first, sa, sb)
    preds["tet12_framesnap"] = snap_12tet(y)
    for name, phi in (("linear", u), ("cosine_module1", (1 - np.cos(np.pi * u)) / 2)):
        A = np.column_stack([1 - phi, phi])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        preds[name] = A @ coef
    preds["plateau_ramp"] = _fit_plateau(y, "lin")
    preds["plateau_cosine"] = _fit_plateau(y, "cos")
    return preds


def _fit_sinusoid(y: np.ndarray, dt: float, drift: bool = False, f_lo=None, f_hi=7.0):
    t = np.arange(len(y)) * dt
    f_lo = min(0.8, 2.0 / (len(y) * dt)) if f_lo is None else f_lo   # >= 2 cycles; 0.8 Hz for 2 s windows

    def design(f):
        cols = [np.ones_like(t)] + ([t] if drift else []) + [np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)]
        return np.column_stack(cols)

    def sse(f):
        A = design(f)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        fit = A @ coef
        r = y - fit
        return float(r @ r), fit

    grid = np.arange(f_lo, f_hi, 0.05)
    best = grid[int(np.argmin([sse(f)[0] for f in grid]))]
    res = minimize_scalar(lambda f: sse(f)[0], bounds=(max(f_lo, best - 0.06), min(f_hi, best + 0.06)),
                          method="bounded")
    return sse(res.x)[1], float(res.x)


def fit_osc(y: np.ndarray, dt: float = 0.01) -> dict:
    n = len(y)
    t = np.arange(n) * dt
    preds = {
        "tet12_note": np.full(n, float(snap_12tet(np.median(y)))),
        "shruti22_note": np.full(n, float(snap_shruti(np.median(y))[0])),
        "tet12_framesnap": snap_12tet(y),
        "steady_free": np.full(n, float(np.mean(y))),
    }
    coef = np.polyfit(t, y, 1)
    preds["linear_drift"] = np.polyval(coef, t)
    preds["sinusoid_module1"], _ = _fit_sinusoid(y, dt, drift=False)
    preds["sinusoid_drift"], _ = _fit_sinusoid(y, dt, drift=True)
    return preds


def fit_segment(kind: str, y: np.ndarray, dt: float = 0.01):
    return fit_glide(y, dt) if kind == "glide" else fit_osc(y, dt)


def metrics(y: np.ndarray, p: np.ndarray, model: str = "") -> dict:
    e = y - p
    n = len(y)
    sse = float(e @ e)
    k = N_PARAMS.get(model)
    aicc = np.nan
    if k is not None:
        n_eff = max(n / 5.0, k + 3.0)          # ~50 ms decorrelation (5 frames) -> effective samples
        aic = n_eff * np.log(max(sse / n, 1e-12)) + 2 * k
        aicc = aic + 2 * k * (k + 1) / (n_eff - k - 1)
    return {"rmse": float(np.sqrt(sse / n)), "mae": float(np.mean(np.abs(e))),
            "p95_abs": float(np.percentile(np.abs(e), 95)), "aicc": float(aicc)}


def glide_params(y: np.ndarray) -> dict:
    """Fitted hold-ramp-hold parameters of one glide: start/end pitch (cents), ramp onset/offset as
    fractions of the segment, and mean ramp slope (cents per second of ramp)."""
    n = len(y)
    u = np.linspace(0.0, 1.0, n)
    t1 = np.linspace(0.0, 0.45, 19)
    t2 = np.linspace(0.55, 1.0, 19)
    T1, T2 = np.meshgrid(t1, t2, indexing="ij")
    T1f, T2f = T1.ravel(), T2.ravel()
    phi = np.clip((u[None, :] - T1f[:, None]) / (T2f - T1f)[:, None], 0.0, 1.0)
    w = 1.0 - phi
    s11, s12, s22 = (w * w).sum(1), (w * phi).sum(1), (phi * phi).sum(1)
    r1, r2 = (w * y).sum(1), (phi * y).sum(1)
    det = s11 * s22 - s12 ** 2
    det = np.where(np.abs(det) < 1e-12, 1e-12, det)
    a = (r1 * s22 - r2 * s12) / det
    b = (r2 * s11 - r1 * s12) / det
    pred = a[:, None] * w + b[:, None] * phi
    i = int(np.argmin(((y[None, :] - pred) ** 2).sum(1)))
    dur = n * 0.01
    ramp_s = max((T2f[i] - T1f[i]) * dur, 1e-3)
    return dict(start=float(a[i]), end=float(b[i]), onset=float(T1f[i]), offset=float(T2f[i]),
                ramp_frac=float(T2f[i] - T1f[i]), slope=float((b[i] - a[i]) / ramp_s), duration=dur)


def osc_params(y: np.ndarray, dt: float = 0.01) -> dict:
    """Fitted sinusoid-with-drift parameters of one oscillation: frequency (Hz), amplitude (cents),
    centre (cents, at mid-segment) and total drift across the segment (cents)."""
    t = np.arange(len(y)) * dt

    def fit(f):
        A = np.column_stack([np.ones_like(t), t, np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = y - A @ coef
        return float(r @ r), coef

    T = len(y) * dt
    f_lo = min(0.8, 2.0 / T)
    grid = np.arange(f_lo, 7.0, 0.05)
    best = grid[int(np.argmin([fit(f)[0] for f in grid]))]
    res = minimize_scalar(lambda f: fit(f)[0], bounds=(max(f_lo, best - 0.06), min(7.0, best + 0.06)), method="bounded")
    _, c = fit(res.x)
    return dict(freq=float(res.x), amp=float(np.hypot(c[2], c[3])), centre=float(c[0] + c[1] * T / 2),
                drift=float(c[1] * T), duration=T)
