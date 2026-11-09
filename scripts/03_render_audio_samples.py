#!/usr/bin/env python
"""Render listening samples: the tracked contour vs each model, same synthetic timbre.

Writes <results>/audio/<kind>_<k>_{reference,module1,...}.wav plus a combined A/B file per
example (reference, then each model, separated by 0.4 s silence) and a manifest CSV.
Examples are the same quantile-spaced ones used in the figures.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ornfid import plots
from ornfid.audio import concat_with_gaps, synth, write_wav
from ornfid.models import PLOT_MODELS, fit_segment
from ornfid.pipeline import load_results, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--n-examples", type=int, default=6)
    a = ap.parse_args()
    contours, seg_meta, res, _ = load_results(a.results)
    out = a.results / "audio"
    out.mkdir(exist_ok=True)
    rows = []
    for kind, models in (("glide", PLOT_MODELS["glide"]), ("osc", PLOT_MODELS["osc"])):
        for k, sid in enumerate(plots.pick_examples(seg_meta, res, kind, a.n_examples), 1):
            y, tonic = contours[sid], float(seg_meta.iloc[sid].tonic_hz)
            preds = fit_segment(kind, y)
            waves = {"reference": synth(y, tonic)}
            waves.update({m: synth(preds[m], tonic) for m in models})
            for name, w in waves.items():
                write_wav(out / f"{kind}_{k:02d}_{name}.wav", w)
            write_wav(out / f"{kind}_{k:02d}_ALL.wav", concat_with_gaps(list(waves.values())))
            rows.append(dict(example=f"{kind}_{k:02d}", seg_id=sid, rec_id=seg_meta.iloc[sid].rec_id,
                             order_in_ALL_file=" -> ".join(waves.keys())))
    pd.DataFrame(rows).to_csv(out / "manifest.csv", index=False, encoding="utf-8")
    log(f"Wrote {len(rows)} example sets to {out}")


if __name__ == "__main__":
    main()
