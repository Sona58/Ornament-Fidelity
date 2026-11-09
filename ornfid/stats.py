"""Summary statistics: segment-level and recording-level, paired tests vs Module 1."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from .models import PARAMETRIC, REFERENCES


def boot_ci_median(x, n_boot=2000, seed=0, alpha=0.05):
    x = np.asarray(x, float)
    if x.size == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    meds = np.median(rng.choice(x, size=(n_boot, x.size), replace=True), axis=1)
    return (float(np.quantile(meds, alpha / 2)), float(np.quantile(meds, 1 - alpha / 2)))


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    out = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        out[i] = min(1.0, running)
    return out


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (kind, model), g in df.groupby(["ornament", "model"], sort=False):
        lo, hi = boot_ci_median(g["rmse"].values)
        rec = g.groupby("rec_id")["rmse"].mean()
        rows.append(dict(ornament=kind, model=model, n_segments=len(g), n_recordings=rec.size,
                         rmse_median=g["rmse"].median(), rmse_median_ci_lo=lo, rmse_median_ci_hi=hi,
                         rmse_q25=g["rmse"].quantile(.25), rmse_q75=g["rmse"].quantile(.75),
                         rmse_mean=g["rmse"].mean(), mae_median=g["mae"].median(),
                         p95_abs_median=g["p95_abs"].median(),
                         rec_level_rmse_mean=rec.mean()))
    return pd.DataFrame(rows)


def paired_vs_module1(df: pd.DataFrame) -> pd.DataFrame:
    """Recording-level paired Wilcoxon (mean RMSE per recording) of every other model vs each
    reference model (original Module 1 and the extended 'Module 1+'), Holm-corrected within
    each (ornament, reference). Also the segment-level win-rate of the reference."""
    rows = []
    for kind in df["ornament"].unique():
        d = df[df.ornament == kind]
        rec = d.pivot_table(index="rec_id", columns="model", values="rmse", aggfunc="mean")
        seg = d.pivot_table(index="seg_id", columns="model", values="rmse", aggfunc="mean")
        for ref in REFERENCES[kind]:
            if ref not in rec.columns:
                continue
            block, pv = [], []
            for m in [c for c in rec.columns if c != ref]:
                diff = (rec[m] - rec[ref]).dropna()   # >0 means reference is better
                try:
                    p = wilcoxon(diff.values, zero_method="wilcox").pvalue if len(diff) >= 6 and np.any(diff != 0) else np.nan
                except ValueError:
                    p = np.nan
                win = float((seg[ref] < seg[m]).mean()) if m in seg else np.nan
                block.append(dict(ornament=kind, baseline=m, reference=ref, n_recordings=len(diff),
                                  median_rec_diff_rmse=float(diff.median()) if len(diff) else np.nan,
                                  segment_winrate_reference=win, wilcoxon_p=p))
                pv.append(p)
            pv = np.array(pv, float)
            ok = np.isfinite(pv)
            corr = np.full_like(pv, np.nan)
            if ok.any():
                corr[ok] = holm(pv[ok])
            for r, c in zip(block, corr):
                r["p_holm"] = float(c)
            rows += block
    return pd.DataFrame(rows)


def aicc_winners(df: pd.DataFrame) -> pd.DataFrame:
    """Among parametric models only: share of segments where each has the lowest AICc
    (complexity-penalised, so a 4-parameter model cannot win just by having more freedom)."""
    rows = []
    for kind, models in PARAMETRIC.items():
        d = df[(df.ornament == kind) & (df.model.isin(models))]
        if d.empty:
            continue
        w = d.pivot_table(index="seg_id", columns="model", values="aicc", aggfunc="mean")
        best = w.idxmin(axis=1).value_counts(normalize=True)
        for m in models:
            rows.append(dict(ornament=kind, model=m, share_best_aicc=float(best.get(m, 0.0))))
    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame, floatfmt="{:.2f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(floatfmt.format(v) if isinstance(v, (float, np.floating)) and np.isfinite(v)
                         else ("" if isinstance(v, float) and not np.isfinite(v) else str(v)))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)
