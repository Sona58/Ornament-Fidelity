#!/usr/bin/env python
"""Copy only the shareable files of one results folder into paper_results/<name>/.

Keeps small CSV/MD/figure outputs; drops audio clips, review pages and (by default) contours;
removes local paths from config.json and recordings.csv/manifest_used.csv/features.csv.

  python tools/prepare_paper_results.py --src results_iw --dst paper_results/main_interior_wide \
      --labels audit_labels_4way.csv="C:\\Downloads\\audit_labels_iw_4way.csv" \
               audit_labels_yesno.csv="C:\\Downloads\\audit_labels_iw.csv"

Add --include-contours only if the corpus licence allows redistributing pitch contours.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

import pandas as pd

KEEP = ["summary.csv", "paired_tests.csv", "aicc_winners.csv", "results_summary.md", "summary_osc_by_frequency_band.csv",
        "fit_results.csv", "segments.csv", "audit_sheet.csv", "audit_precision.csv", "audit_precision_by_band.csv",
        "class_counts.csv", "classification_results.csv", "paired_differences.csv", "sensitivity.csv",
        "sensitivity_median_rmse_glide.csv", "sensitivity_median_rmse_osc.csv"]
PATH_COLS = ["folder", "pitch_file", "audio_file"]


def clean_config(cfg: dict) -> dict:
    args = cfg.get("args", {})
    for k, v in list(args.items()):
        if k == "saraga_root":
            args[k] = "<SARAGA_ROOT>"
        elif isinstance(v, str) and re.search(r"[\\/]", v):
            args[k] = re.split(r"[\\/]", v.strip("[]'\" "))[-1]
    cfg["args"] = args
    return cfg


def clean_table(path: Path, dst: Path):
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in PATH_COLS if c in df.columns])
    df.to_csv(dst, index=False, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--dst", required=True, type=Path)
    ap.add_argument("--labels", nargs="*", default=[], help="NAME=PATH pairs: downloaded audit label files to store")
    ap.add_argument("--include-contours", action="store_true")
    a = ap.parse_args()
    a.dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in KEEP:
        p = a.src / name
        if p.exists():
            shutil.copy2(p, a.dst / name)
            copied.append(name)
    if (a.src / "recordings.csv").exists():
        clean_table(a.src / "recordings.csv", a.dst / "recordings.csv")
        copied.append("recordings.csv (paths removed)")
    for name in ("features.csv", "manifest_used.csv"):
        if (a.src / name).exists():
            clean_table(a.src / name, a.dst / name)
            copied.append(f"{name} (paths removed)")
    if (a.src / "config.json").exists():
        cfg = clean_config(json.loads((a.src / "config.json").read_text(encoding="utf-8")))
        (a.dst / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        copied.append("config.json (sanitised)")
    fig = a.src / "figures"
    if fig.exists():
        (a.dst / "figures").mkdir(exist_ok=True)
        for f in list(fig.glob("*.png")) + list(fig.glob("*.pdf")):
            if "spectrogram" in f.name:        # derived from copyrighted audio
                continue
            shutil.copy2(f, a.dst / "figures" / f.name)
            copied.append(f"figures/{f.name}")
    if a.include_contours and (a.src / "segments_contours.npz").exists():
        shutil.copy2(a.src / "segments_contours.npz", a.dst / "segments_contours.npz")
        copied.append("segments_contours.npz")
    for pair in a.labels:
        name, _, path = pair.partition("=")
        shutil.copy2(path.strip('"'), a.dst / name)
        copied.append(name)
    print(f"Copied {len(copied)} items to {a.dst}:")
    for c in copied:
        print("  ", c)
    skipped = [p.name for p in a.src.iterdir() if p.name in ("audit", "audio")]
    if skipped:
        print("Not copied (audio / review pages):", ", ".join(skipped))


if __name__ == "__main__":
    main()
