"""Figures. All saved as 300-dpi PNG and vector PDF."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .models import GLIDE_MODELS, OSC_MODELS, MODULE1, PLOT_MODELS, fit_segment

LABELS = {
    "tet12_notes": "12-TET two-note (MIDI-style)", "shruti22_notes": "22-shruti two-note",
    "tet12_framesnap": "12-TET frame snap", "linear": "linear glide",
    "cosine_module1": "cosine-eased (Module 1)", "plateau_ramp": "plateau + linear ramp",
    "plateau_cosine": "plateau + cosine ramp (Module 1+)",
    "tet12_note": "12-TET single note", "shruti22_note": "22-shruti single note",
    "steady_free": "steady note (unquantised)", "linear_drift": "linear drift",
    "sinusoid_module1": "sinusoid (Module 1)", "sinusoid_drift": "sinusoid + drift (Module 1+)",
}
COLORS = {
    "tet12_notes": "#999999", "shruti22_notes": "#bbbb44", "tet12_framesnap": "#cccccc", "linear": "#3b7dd8",
    "cosine_module1": "#d62728", "plateau_ramp": "#2ca02c", "plateau_cosine": "#ff7f0e",
    "tet12_note": "#999999", "shruti22_note": "#bbbb44", "steady_free": "#3b7dd8", "linear_drift": "#2ca02c",
    "sinusoid_module1": "#d62728", "sinusoid_drift": "#ff7f0e",
}


def _save(fig, outbase: Path):
    fig.savefig(str(outbase) + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(str(outbase) + ".pdf", bbox_inches="tight")
    plt.close(fig)


def pick_examples(seg_meta, results_df, kind: str, n: int = 6):
    """Deterministic, non-cherry-picked: segments at evenly spaced quantiles of the
    Module-1 RMSE distribution (best ... worst)."""
    ref = MODULE1[kind]
    d = results_df[(results_df.ornament == kind) & (results_df.model == ref)].sort_values("rmse")
    if d.empty:
        return []
    qs = np.linspace(0.05, 0.95, n)
    idx = sorted({int(round(q * (len(d) - 1))) for q in qs})
    return d.iloc[idx]["seg_id"].tolist()


def example_figure(contours, seg_meta, results_df, kind: str, outbase: Path, n: int = 6):
    ids = pick_examples(seg_meta, results_df, kind, n)
    if not ids:
        return
    models = PLOT_MODELS[kind]
    ncol = 3
    nrow = int(np.ceil(len(ids) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.0 * nrow), squeeze=False)
    for ax, sid in zip(axes.ravel(), ids):
        y = contours[sid]
        t = np.arange(len(y)) * 0.01
        preds = fit_segment(kind, y)
        ax.plot(t, y, color="k", lw=2.0, label="tracked f0 (reference)")
        for m in models:
            lw = 1.8 if m in (MODULE1[kind], "plateau_cosine", "sinusoid_drift") else 1.0
            ls = "-" if m in (MODULE1[kind], "plateau_cosine", "sinusoid_drift") else "--"
            ax.plot(t, preds[m], color=COLORS[m], lw=lw, ls=ls, label=LABELS[m])
        r = results_df[(results_df.seg_id == sid) & (results_df.model == MODULE1[kind])].iloc[0]["rmse"]
        meta = seg_meta.iloc[sid]
        ax.set_title(f"{meta['rec_id']} seg {sid}  (Module 1 RMSE {r:.1f} c)", fontsize=8)
        ax.set_xlabel("time (s)", fontsize=8)
        ax.set_ylabel("cents re tonic", fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in axes.ravel()[len(ids):]:
        ax.axis("off")
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=8, frameon=False)
    fig.suptitle(f"{'Meend-like glides' if kind == 'glide' else 'Andolan-like oscillations'}: "
                 "examples at evenly spaced RMSE quantiles (not cherry-picked)", fontsize=10)
    fig.tight_layout(rect=(0, 0.08, 1, 0.96))
    _save(fig, outbase)


def rmse_distribution_figure(results_df, outbase: Path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6))
    for ax, kind, models in zip(axes, ("glide", "osc"), (GLIDE_MODELS, OSC_MODELS)):
        data = [results_df[(results_df.ornament == kind) & (results_df.model == m)]["rmse"].values
                for m in models]
        if not any(len(d) for d in data):
            ax.axis("off")
            continue
        bp = ax.boxplot(data, vert=True, patch_artist=True, showfliers=False)
        for patch, m in zip(bp["boxes"], models):
            patch.set_facecolor(COLORS[m])
            patch.set_alpha(0.7)
        ax.set_xticks(range(1, len(models) + 1))
        ax.set_xticklabels([LABELS[m].replace(" (", "\n(") for m in models], fontsize=6, rotation=25)
        ax.set_ylabel("reconstruction RMSE (cents)")
        ax.set_title(("Meend-like glides" if kind == "glide" else "Andolan-like oscillations")
                     + f"  (n = {len(data[0])})", fontsize=10)
    fig.tight_layout()
    _save(fig, outbase)


def spectrogram_figure(audio_path, tonic_hz, t_start_abs, y, preds, kind, outbase: Path,
                       context_s: float = 1.0, f_max: float = 1500.0):
    """Optional. Needs librosa (+ ffmpeg for mp3). Spectrogram of the vocal audio around a
    segment, with tracked f0 (white) and Module-1 fit (red) overlaid."""
    import librosa
    from scipy.signal import spectrogram
    dur = len(y) * 0.01
    off = max(0.0, t_start_abs - context_s)
    sig, sr = librosa.load(str(audio_path), sr=22050, mono=True, offset=off, duration=dur + 2 * context_s)
    f, tt, S = spectrogram(sig, fs=sr, nperseg=4096, noverlap=4096 - 256, window="hann")
    S_db = 10 * np.log10(S + 1e-12)
    S_db = np.maximum(S_db, S_db.max() - 70)
    fig, ax = plt.subplots(figsize=(6, 3.4))
    m = f <= f_max
    ax.pcolormesh(tt + off - t_start_abs, f[m], S_db[m], shading="auto", cmap="magma")
    tr = np.arange(len(y)) * 0.01
    ax.plot(tr, tonic_hz * 2 ** (y / 1200), color="white", lw=1.2, label="tracked f0")
    ax.plot(tr, tonic_hz * 2 ** (preds / 1200), color="#ff4444", lw=1.2, ls="--", label="Module 1 fit")
    ax.set_xlabel("time from segment start (s)")
    ax.set_ylabel("frequency (Hz)")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(f"{kind} example", fontsize=9)
    _save(fig, outbase)
