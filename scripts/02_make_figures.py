#!/usr/bin/env python
"""Experiment 2: figures from the results of script 01.

    python scripts\\02_make_figures.py --results results
    python scripts\\02_make_figures.py --results results --spectrograms   # needs librosa (+ffmpeg for mp3)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ornfid import plots
from ornfid.models import MODULE1, fit_segment
from ornfid.pipeline import load_results, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--n-examples", type=int, default=6)
    ap.add_argument("--spectrograms", action="store_true")
    a = ap.parse_args()
    contours, seg_meta, res, recs = load_results(a.results)
    fig_dir = a.results / "figures"
    fig_dir.mkdir(exist_ok=True)
    for kind, name in (("glide", "fig_glide_examples"), ("osc", "fig_oscillation_examples")):
        plots.example_figure(contours, seg_meta, res, kind, fig_dir / name, a.n_examples)
    plots.rmse_distribution_figure(res, fig_dir / "fig_rmse_distributions")
    log(f"Wrote line/box figures to {fig_dir}")
    if a.spectrograms:
        for kind in ("glide", "osc"):
            ids = plots.pick_examples(seg_meta, res, kind, 3)
            for sid in ids:
                m = seg_meta.iloc[sid]
                audio = recs.loc[recs.rec_id == m.rec_id, "audio_file"].iloc[0]
                if not isinstance(audio, str) or not audio:
                    log(f"seg {sid}: no audio file found, skipping spectrogram")
                    continue
                try:
                    pred = fit_segment(kind, contours[sid])[MODULE1[kind]]
                    plots.spectrogram_figure(audio, m.tonic_hz, m.t_start_abs, contours[sid], pred, kind,
                                             fig_dir / f"fig_spectrogram_{kind}_seg{sid}")
                    log(f"spectrogram written for seg {sid}")
                except Exception as e:  # noqa: BLE001
                    log(f"seg {sid}: spectrogram failed ({type(e).__name__}: {e}). "
                        "On Windows, mp3 decoding needs ffmpeg on PATH.")


if __name__ == "__main__":
    main()
