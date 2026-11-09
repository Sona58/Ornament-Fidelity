#!/usr/bin/env python
"""Sensitivity of the headline comparisons to the detector's thresholds.

Reviewers will ask whether results depend on arbitrary thresholds. This reruns detection+fitting
under several settings (pitch files are read once) and tabulates, per setting, the number of
segments, median RMSE of every model and the AICc winner shares.

    python scripts\\05_sensitivity.py --saraga-root "D:\\...\\saraga_hindustani" --out results_sens
Use --max-recordings 30 for a quicker run.
"""
import argparse
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ornfid import detect, io_saraga as io, stats
from ornfid.pipeline import detect_in_runs, fit_all, log, prepare_recording

G, O = detect.GlideParams(), detect.OscParams()
SETTINGS = {
    "baseline": (G, O),
    "glide_min_slope_75": (replace(G, min_slope=75.0), O),
    "glide_min_slope_150": (replace(G, min_slope=150.0), O),
    "glide_min_excursion_150": (replace(G, min_excursion=150.0), O),
    "glide_min_excursion_200": (replace(G, min_excursion=200.0), O),
    "glide_min_dur_0.6": (replace(G, min_dur=0.6), O),
    "glide_no_boundary_extension": (replace(G, max_extend=0), O),
    "osc_peak_frac_0.7": (G, replace(O, min_peak_frac=0.7)),
    "osc_amp_25_100": (G, replace(O, amp_lo=25.0, amp_hi=100.0)),
    "osc_window_1.5s": (G, replace(O, window=1.5)),
    "osc_dev_ratio_2.5": (G, replace(O, max_dev_ratio=2.5)),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saraga-root", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path("results_sens"))
    ap.add_argument("--max-recordings", type=int, default=None)
    ap.add_argument("--max-seg-per-rec", type=int, default=None)
    ap.add_argument("--exclude-list", help="same list format as script 01 (path after the Saraga root)")
    ap.add_argument("--include-list")
    ap.add_argument("--ignore-unmatched", action="store_true")
    a = ap.parse_args()
    recs = io.find_recordings(a.saraga_root)
    recs = io.apply_lists(recs, a.saraga_root, a.include_list, a.exclude_list, a.ignore_unmatched, log)
    if a.max_recordings:
        recs = recs[: a.max_recordings]
    prepared = []
    for k, r in enumerate(recs, 1):
        tonic = io.read_tonic(r)
        if tonic is None:
            log(f"[{r.rec_id}] no tonic file, skipped")
            continue
        t, f0 = io.read_pitch(r.pitch_file)
        runs, voiced = prepare_recording(t, f0, tonic)
        if voiced >= 30:
            prepared.append((r.rec_id, tonic, runs))
        log(f"prepared {k}/{len(recs)}")
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (gp, op) in SETTINGS.items():
        seg_rows, contours = [], []
        for rec_id, tonic, runs in prepared:
            for f in detect_in_runs(runs, gp, op, a.max_seg_per_rec):
                contours.append(f.pop("y"))
                seg_rows.append(dict(rec_id=rec_id, tonic_hz=tonic, **f))
        if not seg_rows:
            log(f"{name}: no segments")
            continue
        seg = pd.DataFrame(seg_rows)
        res = fit_all(seg, contours)
        summ = stats.summarize(res)
        aic = stats.aicc_winners(res)
        for (kind, model), g in res.groupby(["ornament", "model"]):
            w = aic[(aic.ornament == kind) & (aic.model == model)]["share_best_aicc"]
            rows.append(dict(setting=name, ornament=kind, model=model, n_segments=int((seg.ornament == kind).sum()),
                             rmse_median=g["rmse"].median(), share_best_aicc=float(w.iloc[0]) if len(w) else float("nan")))
        log(f"done {name}: {len(seg)} segments")
    out = pd.DataFrame(rows)
    out.to_csv(a.out / "sensitivity.csv", index=False, encoding="utf-8")
    for kind in ("glide", "osc"):
        piv = out[out.ornament == kind].pivot_table(index="setting", columns="model", values="rmse_median", sort=False)
        n = out[out.ornament == kind].groupby("setting", sort=False)["n_segments"].first()
        piv.insert(0, "n_segments", n)
        piv.round(2).to_csv(a.out / f"sensitivity_median_rmse_{kind}.csv", encoding="utf-8")
        log(f"\n=== {kind}: median RMSE (cents) by setting ===\n{piv.round(1).to_string()}")


if __name__ == "__main__":
    main()
