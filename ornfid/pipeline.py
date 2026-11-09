"""Shared helpers: run detection+fitting for one recording; load saved results."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import detect, preprocess as pp
from .models import fit_segment, metrics


def log(msg: str):
    print(str(msg).encode("ascii", "replace").decode("ascii"), flush=True)


def prepare_recording(t, f0, tonic_hz):
    """Gap-fill, split into voiced runs, median-filter. Returns (list of (y_run, t_start_abs), voiced_s)."""
    tg, c = pp.to_cents_grid(t, f0, tonic_hz)
    if tg.size == 0:
        return [], 0.0
    runs = pp.voiced_runs(c)
    prepared = [(pp.clean_run(c[i0:i1]), float(tg[i0])) for i0, i1 in runs]
    voiced_s = float(sum(i1 - i0 for i0, i1 in runs) * pp.HOP_S)
    return prepared, voiced_s


def detect_in_runs(prepared, glide_p=None, osc_p=None, max_seg_per_rec=None):
    glide_p = glide_p or detect.GlideParams()
    osc_p = osc_p or detect.OscParams()
    found = []
    for run_id, (y, t0) in enumerate(prepared):
        for kind, dets in (("glide", detect.detect_glides(y, glide_p)), ("osc", detect.detect_oscillations(y, osc_p))):
            for d in dets:
                a, b = d["i0"], d["i1"] + 1
                found.append(dict(ornament=kind, run_id=run_id, y=y[a:b].copy(), t_start_abs=t0 + a * pp.HOP_S,
                                  **{k: v for k, v in d.items() if k not in ("i0", "i1")}))
    if max_seg_per_rec and len(found) > max_seg_per_rec:
        rng = np.random.default_rng(0)
        keep = sorted(rng.choice(len(found), max_seg_per_rec, replace=False))
        found = [found[i] for i in keep]
    return found


def process_recording(t, f0, tonic_hz, max_seg_per_rec=None):
    prepared, voiced_s = prepare_recording(t, f0, tonic_hz)
    return detect_in_runs(prepared, max_seg_per_rec=max_seg_per_rec), voiced_s


def fit_all(segments_meta: pd.DataFrame, contours: list[np.ndarray]) -> pd.DataFrame:
    rows = []
    for sid, (m, y) in enumerate(zip(segments_meta.itertuples(index=False), contours)):
        preds = fit_segment(m.ornament, y)
        for name, p in preds.items():
            rows.append(dict(seg_id=sid, rec_id=m.rec_id, ornament=m.ornament, model=name, **metrics(y, p, name)))
    return pd.DataFrame(rows)


def save_contours(path: Path, contours: list[np.ndarray]):
    offsets = np.cumsum([0] + [len(y) for y in contours])
    np.savez_compressed(path, y_all=np.concatenate(contours) if contours else np.array([]), offsets=offsets)


def load_results(out_dir: Path):
    out_dir = Path(out_dir)
    z = np.load(out_dir / "segments_contours.npz")
    y_all, off = z["y_all"], z["offsets"]
    contours = [y_all[off[i]:off[i + 1]] for i in range(len(off) - 1)]
    seg_meta = pd.read_csv(out_dir / "segments.csv")
    results = pd.read_csv(out_dir / "fit_results.csv")
    recs = pd.read_csv(out_dir / "recordings.csv")
    return contours, seg_meta, results, recs
