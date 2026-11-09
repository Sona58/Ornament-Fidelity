#!/usr/bin/env python
"""Experiment 1: how faithfully do different representations reconstruct real ornaments?

Detects meend-like glides and andolan-like oscillations in Saraga Hindustani pitch
tracks, fits each candidate representation, and reports reconstruction error in cents.

Example (Windows, from the repo root):
    python scripts\\01_run_reconstruction.py --saraga-root "D:\\data\\saraga1.5_hindustani" --out results
Dry run (lists what was found, no processing):
    python scripts\\01_run_reconstruction.py --saraga-root "D:\\data\\saraga1.5_hindustani" --list-only
"""
import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ornfid import __version__, detect, io_saraga as io, stats
from ornfid.pipeline import detect_in_runs, fit_all, log, prepare_recording, save_contours


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saraga-root", required=True, type=Path, help="folder containing the Saraga Hindustani data")
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--exclude-list", help="text file, one recording per line, as the path after the Saraga root: "
                    "<release folder>\\<raag folder>\\<recording name>  (see --write-keys)")
    ap.add_argument("--include-list", help="same format; keep only these recordings (e.g. your 98-recording set)")
    ap.add_argument("--ignore-unmatched", action="store_true",
                    help="do not stop when a list entry matches nothing / is ambiguous")
    ap.add_argument("--write-keys", type=Path,
                    help="write the exact key of every recording found (one per line) to this file, to copy from")
    ap.add_argument("--max-recordings", type=int, default=None, help="quick test on the first N recordings")
    ap.add_argument("--max-seg-per-rec", type=int, default=None)
    ap.add_argument("--audit-glide", type=int, default=30, help="number of glide-like segments in the audit sheet")
    ap.add_argument("--audit-osc", type=int, default=30, help="number of oscillation-like segments in the audit sheet")
    ap.add_argument("--audit-exclude", nargs="*", default=[],
                    help="earlier audit_sheet.csv file(s): segments within 0.5 s of an already-audited one are not re-sampled")
    ap.add_argument("--min-voiced-s", type=float, default=30.0, help="skip recordings with less voiced audio")
    ap.add_argument("--allow-estimated-tonic", action="store_true",
                    help="continue even if some recordings have no tonic file (NOT recommended)")
    ap.add_argument("--osc-preset", choices=sorted(detect.OSC_PRESETS), default="default",
                    help="oscillation detector preset (strict-osc = slower, more regular oscillations only)")
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    recs = io.find_recordings(a.saraga_root)
    log(f"Found {len(recs)} recordings with pitch files under {a.saraga_root}")
    if a.write_keys:
        a.write_keys.write_text("\n".join(r.key.replace("/", "\\") for r in recs) + "\n", encoding="utf-8")
        log(f"Wrote {len(recs)} recording keys to {a.write_keys}")
    recs = io.apply_lists(recs, a.saraga_root, a.include_list, a.exclude_list, a.ignore_unmatched, log)
    if a.max_recordings:
        recs = recs[: a.max_recordings]
    log(f"Using {len(recs)} recordings after include/exclude filters")
    kinds = pd.Series([r.pitch_kind for r in recs]).value_counts().to_dict()
    log(f"Pitch-file kinds: {kinds};  with tonic file: {sum(r.tonic_file is not None for r in recs)};  "
        f"with audio: {sum(r.audio_file is not None for r in recs)}")
    n_no_tonic = sum(io.read_tonic(r) is None for r in recs)
    log(f"Recordings WITHOUT a readable tonic file: {n_no_tonic} of {len(recs)}")
    if n_no_tonic and not a.list_only and not a.allow_estimated_tonic:
        log("Stopping: tonic files missing (looked for <stem>.ctonic / .ctonic.txt / .tonic.txt in each track folder).\n"
            "Fix, or rerun with --allow-estimated-tonic to use a histogram-based estimate.")
        return
    if a.list_only or not recs:
        for r in recs[:15]:
            log(f"  {r.rec_id}  {r.key}  [{r.pitch_kind}]")
        return

    a.out.mkdir(parents=True, exist_ok=True)
    seg_rows, contours, rec_rows = [], [], []
    for k, r in enumerate(recs, 1):
        try:
            t, f0 = io.read_pitch(r.pitch_file)
        except Exception as e:  # noqa: BLE001
            log(f"[{r.rec_id}] SKIP unreadable pitch file: {e}")
            continue
        tonic, src = io.read_tonic(r), "file"
        if tonic is None:
            tonic, src = io.estimate_tonic_from_histogram(f0[f0 > 0]), "ESTIMATED"
        prepared, voiced_s = prepare_recording(t, f0, tonic)
        found = detect_in_runs(prepared, None, detect.OSC_PRESETS[a.osc_preset], a.max_seg_per_rec)
        rec_rows.append(dict(rec_id=r.rec_id, rel_key=r.key, stem=r.stem, folder=str(r.folder), pitch_file=r.pitch_file.name,
                             pitch_kind=r.pitch_kind, audio_file=str(r.audio_file) if r.audio_file else "",
                             tonic_hz=tonic, tonic_source=src, voiced_s=voiced_s,
                             n_glide=sum(f["ornament"] == "glide" for f in found),
                             n_osc=sum(f["ornament"] == "osc" for f in found),
                             used=voiced_s >= a.min_voiced_s))
        log(f"[{k}/{len(recs)}] {r.rec_id} tonic={tonic:.1f}Hz({src}) voiced={voiced_s:.0f}s "
            f"glides={rec_rows[-1]['n_glide']} osc={rec_rows[-1]['n_osc']}")
        if voiced_s < a.min_voiced_s:
            continue
        for f in found:
            y = f.pop("y")
            contours.append(y)
            seg_rows.append(dict(rec_id=r.rec_id, tonic_hz=tonic, n_frames=len(y), **f))

    recs_df = pd.DataFrame(rec_rows)
    seg_df = pd.DataFrame(seg_rows)
    if seg_df.empty:
        log("No segments detected. Check --list-only output and the detection thresholds in ornfid/detect.py.")
        recs_df.to_csv(a.out / "recordings.csv", index=False, encoding="utf-8")
        return
    seg_df.insert(0, "seg_id", range(len(seg_df)))
    recs_df.to_csv(a.out / "recordings.csv", index=False, encoding="utf-8")
    seg_df.to_csv(a.out / "segments.csv", index=False, encoding="utf-8")
    save_contours(a.out / "segments_contours.npz", contours)

    res = fit_all(seg_df, contours)
    res.to_csv(a.out / "fit_results.csv", index=False, encoding="utf-8")
    summ = stats.summarize(res)
    paired = stats.paired_vs_module1(res)
    summ.to_csv(a.out / "summary.csv", index=False, encoding="utf-8")
    paired.to_csv(a.out / "paired_tests.csv", index=False, encoding="utf-8")
    stats.aicc_winners(res).to_csv(a.out / "aicc_winners.csv", index=False, encoding="utf-8")

    # manual-audit sample (to estimate detector precision by listening / viewing)
    rng = np.random.default_rng(a.seed)
    done = {}
    for fpath in a.audit_exclude:
        prev = pd.read_csv(fpath)
        for rid, t0 in zip(prev.rec_id, prev.t_start_abs):
            done.setdefault(rid, []).append(float(t0))
    parts = []
    for kind, n_aud in (("glide", a.audit_glide), ("osc", a.audit_osc)):
        d = seg_df[seg_df.ornament == kind]
        if done:
            fresh = [not any(abs(t - u) < 0.5 for u in done.get(r, [])) for r, t in zip(d.rec_id, d.t_start_abs)]
            log(f"audit pool ({kind}): {int(np.sum(fresh))} of {len(d)} segments not previously audited")
            d = d[np.array(fresh, dtype=bool)]
        if n_aud > 0 and len(d):
            parts.append(d.sample(min(len(d), n_aud), random_state=a.seed))
    audit = pd.concat(parts)[["seg_id", "rec_id", "ornament", "t_start_abs", "duration"]].copy()
    audit["is_true_ornament_yes_no"] = ""
    audit["notes"] = ""
    audit.to_csv(a.out / "audit_sheet.csv", index=False, encoding="utf-8")

    # oscillation results split by dominant frequency (slow vs fast), a robustness table
    if (seg_df.ornament == "osc").any():
        o = seg_df[seg_df.ornament == "osc"][["seg_id", "freq_hz"]]
        o = o.assign(band=pd.cut(o.freq_hz, [0, 3.0, 4.5, 99], labels=["<3 Hz", "3-4.5 Hz", ">4.5 Hz"]))
        bt = res[res.ornament == "osc"].merge(o, on="seg_id").groupby(["band", "model"], observed=True)["rmse"] \
            .agg(n_segments="size", rmse_median="median").reset_index()
        bt.to_csv(a.out / "summary_osc_by_frequency_band.csv", index=False, encoding="utf-8")
    cfg = dict(version=__version__, python=sys.version, platform=platform.platform(), numpy=np.__version__,
               pandas=pd.__version__, args={k: str(v) for k, v in vars(a).items()}, detector=detect.params_dict(), osc_preset=a.osc_preset, osc_params=vars(detect.OSC_PRESETS[a.osc_preset]),
               n_recordings_used=int(recs_df["used"].sum()), n_segments=len(seg_df),
               tonic_estimated=int((recs_df.tonic_source == "ESTIMATED").sum()))
    (a.out / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    md = ["# Reconstruction results (RMSE in cents, lower = better)\n",
          f"Recordings used: {cfg['n_recordings_used']}; segments: {len(seg_df)} "
          f"({(seg_df.ornament == 'glide').sum()} glide-like, {(seg_df.ornament == 'osc').sum()} oscillation-like).\n",
          "Segments are *detected by signal heuristics*, not human-annotated; see audit_sheet.csv.\n",
          "## Per-model summary\n", stats.to_markdown(summ[["ornament", "model", "n_segments", "rmse_median",
                                                          "rmse_median_ci_lo", "rmse_median_ci_hi", "rmse_q25",
                                                          "rmse_q75", "rec_level_rmse_mean"]]),
          "\n\n## Complexity-penalised comparison (share of segments where each parametric model has the lowest AICc)\n",
          stats.to_markdown(stats.aicc_winners(res), floatfmt="{:.3f}"),
          "\n\n## Paired recording-level tests vs each reference model (Holm-corrected; diff>0 = reference better)\n",
          stats.to_markdown(paired, floatfmt="{:.4g}")]
    (a.out / "results_summary.md").write_text("\n".join(md), encoding="utf-8")
    log("\n".join(md))
    log(f"\nDone. Outputs in {a.out.resolve()}")


if __name__ == "__main__":
    main()
