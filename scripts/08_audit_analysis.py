#!/usr/bin/env python
"""Reproduce the audit-based analyses reported in the paper from the curated result folders.

Expected layout (see docs/PAPER_MAP.md; create it with tools/prepare_paper_results.py):

  paper_results/
    main_interior_wide/        segments.csv  fit_results.csv  [segments_contours.npz]
                               audit_labels_4way.csv  audit_labels_yesno.csv
    slowband_andolan/          segments.csv  audit_labels_4way.csv  audit_labels_yesno.csv
    audit_rounds/round1_default/   segments.csv  audit_labels.csv      (default detector)
    audit_rounds/round2_strict/    segments.csv  audit_labels.csv      (strict-osc detector)

Every file is optional: analyses whose inputs are missing are skipped with a message.

Run:  python scripts/08_audit_analysis.py --paper-results paper_results
Writes <paper-results>/audit_analysis/*.csv and audit_analysis.md.
"""
import argparse
import sys
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ornfid.models import GLIDE_MODELS, PARAMETRIC, fit_glide, glide_params, snap_shruti  # noqa: E402
from ornfid.pipeline import log  # noqa: E402

OSC_TYPES = ["andolan", "kampit", "gamak", "other"]
EDGE_HZ = 1.06          # peaks at or below this frequency are pinned to the lowest band bin (~1.03 Hz)
BAND_HZ = 3.0           # split used for the frequency-band tables


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def fmt_ci(k, n):
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * p:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def read(path):
    path = Path(path)
    return pd.read_csv(path) if path.exists() else None


def labelled(labels, segments, kind, allowed):
    if labels is None or segments is None:
        return None
    lab = labels.copy()
    lab["label"] = lab["label"].astype(str).str.strip().str.lower()
    seg_cols = [c for c in segments.columns if c != "ornament"]
    m = lab[lab.ornament == kind].merge(segments[seg_cols], on="seg_id")
    return m[m.label.isin(allowed)]


# ----------------------------------------------------------------------------------------------
# A. glide precision per audit round and pooled
# ----------------------------------------------------------------------------------------------
def glide_precision(rounds, md):
    rows, k_all, n_all = [], 0, 0
    for name, (labels, segs) in rounds.items():
        g = labelled(labels, segs, "glide", ["yes", "no"])
        if g is None or not len(g):
            continue
        k, n = int((g.label == "yes").sum()), len(g)
        k_all, n_all = k_all + k, n_all + n
        p, lo, hi = wilson(k, n)
        rows.append(dict(audit=name, labelled=n, genuine=k, precision=p, ci95_lo=lo, ci95_hi=hi))
    if n_all:
        p, lo, hi = wilson(k_all, n_all)
        rows.append(dict(audit="pooled", labelled=n_all, genuine=k_all, precision=p, ci95_lo=lo, ci95_hi=hi))
        md.append(f"## A. Glide detector precision (meend / not meend)\n\n"
                  + "\n".join(f"- {r['audit']}: {fmt_ci(r['genuine'], r['labelled'])}" for r in rows) + "\n")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------
# B. oscillation audits: precision, composition, bands, label-scheme effect, detector comparison
# ----------------------------------------------------------------------------------------------
def oscillation_audits(detectors, md):
    rows, comp_rows, band_rows, type_rows, scheme_rows = [], [], [], [], []
    counts = {}
    for name, d in detectors.items():
        four = labelled(d["l4"], d["seg"], "osc", OSC_TYPES)
        if four is None or not len(four):
            continue
        n = len(four)
        any_k = int(four.label.isin(["andolan", "kampit", "gamak"]).sum())
        and_k = int((four.label == "andolan").sum())
        counts[name] = (any_k, n)
        for target, k in (("any oscillatory ornament", any_k), ("andolan only", and_k)):
            p, lo, hi = wilson(k, n)
            rows.append(dict(detector=name, target=target, labelled=n, genuine=k, precision=p, ci95_lo=lo, ci95_hi=hi))
        for t, c in four.label.value_counts().items():
            comp_rows.append(dict(detector=name, label=t, n=int(c)))
        four = four.assign(band=np.where(four.freq_hz <= BAND_HZ, f"<={BAND_HZ:g} Hz", f">{BAND_HZ:g} Hz"))
        for b, g in four.groupby("band"):
            k = int(g.label.isin(["andolan", "kampit", "gamak"]).sum())
            p, lo, hi = wilson(k, len(g))
            band_rows.append(dict(detector=name, band=b, labelled=len(g), any_oscillatory=k, precision=p,
                                  ci95_lo=lo, ci95_hi=hi, types=str(g.label.value_counts().to_dict())))
        for t, g in four.groupby("label"):
            type_rows.append(dict(detector=name, label=t, n=len(g), median_freq_hz=g.freq_hz.median(),
                                  median_amp_cents=g.amp_cents.median()))
        yn = d["lyn"]
        if yn is not None:
            m = yn.merge(d["l4"], on="seg_id", suffixes=("_yn", "_4w"))
            m = m[m.label_4w.astype(str).isin(OSC_TYPES)]
            if len(m):
                tab = pd.crosstab(m.label_yn, m.label_4w)
                tab.insert(0, "detector", name)
                scheme_rows.append(tab.reset_index())
    out = {"osc_precision": pd.DataFrame(rows), "osc_composition": pd.DataFrame(comp_rows),
           "osc_by_band": pd.DataFrame(band_rows), "osc_type_medians": pd.DataFrame(type_rows),
           "label_scheme_crosstab": pd.concat(scheme_rows) if scheme_rows else pd.DataFrame()}
    if rows:
        lines = ["## B. Oscillation audits (four-way labels)\n"]
        for r in rows:
            lines.append(f"- {r['detector']} / {r['target']}: {fmt_ci(r['genuine'], r['labelled'])}")
        if len(counts) == 2:
            (n1, (k1, m1)), (n2, (k2, m2)) = list(counts.items())
            _, pf = fisher_exact([[k1, m1 - k1], [k2, m2 - k2]])
            lines.append(f"- Fisher exact test, {n1} vs {n2} (any oscillatory ornament): p = {pf:.3f}")
        lines.append("\nBy dominant frequency (any oscillatory ornament):\n")
        lines += [f"- {r['detector']} {r['band']}: {fmt_ci(r['any_oscillatory'], r['labelled'])}; types {r['types']}"
                  for r in band_rows]
        md.append("\n".join(lines) + "\n")
    return out


# ----------------------------------------------------------------------------------------------
# C. band-edge artifact (rounds 1 and 2)
# ----------------------------------------------------------------------------------------------
def band_edge(rounds, md):
    rows, lines = [], []
    for name, (labels, segs) in rounds.items():
        if segs is None:
            continue
        o = segs[segs.ornament == "osc"]
        if not len(o):
            continue
        share = float((o.freq_hz <= EDGE_HZ).mean())
        row = dict(audit=name, n_osc_segments=len(o), share_peak_at_band_edge=share)
        y = labelled(labels, segs, "osc", ["yes", "no"])
        if y is not None and len(y):
            y = y.assign(edge=y.freq_hz <= EDGE_HZ)
            for edge in (True, False):
                g = y[y.edge == edge]
                row[f"{'edge' if edge else 'interior'}_genuine"] = int((g.label == "yes").sum())
                row[f"{'edge' if edge else 'interior'}_labelled"] = len(g)
        rows.append(row)
        lines.append(f"- {name}: {100 * share:.1f}% of {len(o)} oscillation-like detections have the spectral peak at the "
                     f"band edge (<= {EDGE_HZ} Hz)" + ("; audited: " + ", ".join(
                         f"{k.split('_')[0]} {row[k]}/{row[k.replace('genuine', 'labelled')]} genuine"
                         for k in row if k.endswith("_genuine")) if any(k.endswith("_genuine") for k in row) else ""))
    if rows:
        md.append("## C. Band-edge artifact (audit rounds 1-2, yes/no labels)\n\n" + "\n".join(lines) + "\n")
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------
# D. rescoring on audited-genuine glides, using the main run's fits
# ----------------------------------------------------------------------------------------------
def map_audited_glides(rounds, main_seg):
    g = main_seg[main_seg.ornament == "glide"]
    rows, dropped = [], 0
    for name, (labels, segs) in rounds.items():
        a = labelled(labels, segs, "glide", ["yes", "no"])
        if a is None:
            continue
        for r in a.itertuples():
            hit = g[(g.rec_id == r.rec_id) & ((g.t_start_abs - r.t_start_abs).abs() < 0.05)]
            if len(hit):
                rows.append(dict(audit=name, main_seg_id=int(hit.iloc[0].seg_id), label=r.label))
            else:
                dropped += 1          # e.g. segments in recordings later excluded
    m = pd.DataFrame(rows).drop_duplicates("main_seg_id") if rows else pd.DataFrame(columns=["audit", "main_seg_id", "label"])
    return m, dropped


def audited_genuine_glides(rounds, main_seg, main_fit, md, seed=0):
    m, dropped = map_audited_glides(rounds, main_seg)
    if m.empty:
        return pd.DataFrame(), m
    rng = np.random.default_rng(seed)
    fit = main_fit[main_fit.ornament == "glide"]
    rows = []
    for lab in ("yes", "no"):
        ids = m[m.label == lab].main_seg_id
        for model in GLIDE_MODELS:
            v = fit[(fit.model == model) & fit.seg_id.isin(ids)].rmse.values
            if not len(v):
                continue
            b = [np.median(rng.choice(v, len(v))) for _ in range(2000)]
            rows.append(dict(subset=f"audited {lab}", n=len(v), model=model, median_rmse=float(np.median(v)),
                             ci_lo=float(np.percentile(b, 2.5)), ci_hi=float(np.percentile(b, 97.5))))
    res = pd.DataFrame(rows)
    yes_ids = m[m.label == "yes"].main_seg_id
    piv = fit[fit.seg_id.isin(yes_ids)].pivot(index="seg_id", columns="model", values="rmse")
    lines = [f"## D. Glide models on audited-genuine meend\n",
             f"Audited glides mapped to the main run: {len(m)} ({int((m.label == 'yes').sum())} genuine, "
             f"{int((m.label == 'no').sum())} not); {dropped} audited glides could not be mapped (e.g. excluded recordings).\n"]
    y = res[res.subset == "audited yes"]
    lines += [f"- {r.model}: {r.median_rmse:.1f} [{r.ci_lo:.1f}, {r.ci_hi:.1f}]" for r in y.itertuples()]
    if {"plateau_ramp", "linear", "cosine_module1", "tet12_framesnap"} <= set(piv.columns):
        lines.append(f"\nWin-rates on genuine glides (n={len(piv)}): plateau_ramp<linear {np.mean(piv.plateau_ramp < piv.linear):.2f}; "
                     f"plateau_ramp<cosine {np.mean(piv.plateau_ramp < piv.cosine_module1):.2f}; "
                     f"plateau_ramp<framesnap {np.mean(piv.plateau_ramp < piv.tet12_framesnap):.2f}; "
                     f"linear<cosine {np.mean(piv.linear < piv.cosine_module1):.2f}")
    a = fit[fit.seg_id.isin(yes_ids) & fit.model.isin(PARAMETRIC["glide"])].pivot(index="seg_id", columns="model", values="aicc")
    if len(a):
        lines.append("AICc winners on genuine glides: " + str(a.idxmin(axis=1).value_counts(normalize=True).round(3).to_dict()))
    full = fit.groupby("model").rmse.median()
    gen = fit[fit.seg_id.isin(yes_ids)].groupby("model").rmse.median()
    common = [x for x in GLIDE_MODELS if x in full.index and x in gen.index]
    if len(common) >= 3:
        lines.append(f"Spearman correlation, full-corpus vs genuine-subset medians: {spearmanr(full[common], gen[common])[0]:.3f}")
    md.append("\n".join(lines) + "\n")
    return res, m


# ----------------------------------------------------------------------------------------------
# E. do contour-shape features separate genuine from non-genuine glides? (permutation test)
# ----------------------------------------------------------------------------------------------
def shape_features(c):
    n, T = len(c), len(c) * 0.01
    p, pr = glide_params(c), fit_glide(c)
    dif = np.diff(c)
    slope = np.abs(dif) / 0.01
    sgn = np.sign(p["end"] - p["start"])
    s_off = abs(p["start"] - snap_shruti(p["start"])[0])
    e_off = abs(p["end"] - snap_shruti(p["end"])[0])
    r_lin = np.sqrt(np.mean((c - pr["linear"]) ** 2))
    r_pl = np.sqrt(np.mean((c - pr["plateau_ramp"]) ** 2))
    return dict(duration=T, abs_excursion=abs(p["end"] - p["start"]), ramp_frac=p["ramp_frac"], abs_slope=abs(p["slope"]),
                max_slope=slope.max(), slope_ratio=slope.max() / (np.median(slope) + 1), zero_diff_frac=(dif == 0).mean(),
                mono_frac=(np.sign(dif) == sgn).mean(), end_shruti_offset=e_off, start_shruti_offset=s_off,
                grid_offset_mean=(s_off + e_off) / 2, rmse_linear=r_lin, rmse_plateau=r_pl,
                plateau_gain=(r_lin - r_pl) / max(r_lin, 1e-6), abs_start=abs(p["start"]), start_cents=p["start"],
                end_cents=p["end"])


def auc(x, y):
    r = pd.Series(x).rank().values
    n1 = int(y.sum())
    n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def shape_feature_test(mapped, contours, md, seed=0, n_boot=1000, n_perm=1000):
    if mapped.empty or contours is None or mapped.label.nunique() < 2:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    F = pd.DataFrame([shape_features(contours[i]) for i in mapped.main_seg_id])
    y = (mapped.label.values == "yes").astype(int)
    cols = list(F.columns)
    obs = {c: auc(F[c].values, y) for c in cols}
    boots = {c: [] for c in cols}
    for _ in range(n_boot):
        i = rng.integers(0, len(F), len(F))
        if y[i].sum() in (0, len(i)):
            continue
        for c in cols:
            boots[c].append(auc(F[c].values[i], y[i]))
    null = [max(abs(auc(F[c].values, rng.permutation(y)) - 0.5) for c in cols) for _ in range(n_perm)]
    thr = float(np.percentile(null, 95))
    res = pd.DataFrame({"AUC": obs, "ci_lo": {c: np.percentile(boots[c], 2.5) for c in cols},
                        "ci_hi": {c: np.percentile(boots[c], 97.5) for c in cols}})
    res["abs_AUC_minus_half"] = (res.AUC - 0.5).abs()
    res = res.sort_values("abs_AUC_minus_half", ascending=False)
    best = float(res.abs_AUC_minus_half.iloc[0])
    md.append(f"## E. Contour-shape features vs audit labels (glides)\n\n{len(cols)} features, n = {len(y)} "
              f"({int(y.sum())} genuine). Largest |AUC - 0.5| = {best:.2f}; permutation 95th percentile of the maximum "
              f"under the null = {thr:.2f}. "
              + ("No feature separates genuine from non-genuine glides beyond chance.\n" if best <= thr else
                 "At least one feature exceeds the permutation threshold.\n"))
    res.attrs["threshold"] = thr
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paper-results", type=Path, default=Path("paper_results"))
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    R = a.paper_results
    out = a.out or R / "audit_analysis"
    out.mkdir(parents=True, exist_ok=True)

    main_d, slow_d = R / "main_interior_wide", R / "slowband_andolan"
    r1, r2 = R / "audit_rounds" / "round1_default", R / "audit_rounds" / "round2_strict"
    rounds = {"round1_default": (read(r1 / "audit_labels.csv"), read(r1 / "segments.csv")),
              "round2_strict": (read(r2 / "audit_labels.csv"), read(r2 / "segments.csv"))}
    detectors = {"broad (interior-wide)": dict(seg=read(main_d / "segments.csv"), l4=read(main_d / "audit_labels_4way.csv"),
                                               lyn=read(main_d / "audit_labels_yesno.csv")),
                 "slow band (andolan preset)": dict(seg=read(slow_d / "segments.csv"), l4=read(slow_d / "audit_labels_4way.csv"),
                                                    lyn=read(slow_d / "audit_labels_yesno.csv"))}
    md = ["# Audit-based analyses (generated by scripts/08_audit_analysis.py)\n"]

    gp = glide_precision(rounds, md)
    if len(gp):
        gp.to_csv(out / "glide_precision.csv", index=False)
    for k, v in oscillation_audits(detectors, md).items():
        if len(v):
            v.to_csv(out / f"{k}.csv", index=False)
    be = band_edge(rounds, md)
    if len(be):
        be.to_csv(out / "band_edge_artifact.csv", index=False)

    main_seg, main_fit = read(main_d / "segments.csv"), read(main_d / "fit_results.csv")
    if main_seg is not None and main_fit is not None:
        res, mapped = audited_genuine_glides(rounds, main_seg, main_fit, md, a.seed)
        if len(res):
            res.to_csv(out / "audited_genuine_glides.csv", index=False)
        npz = main_d / "segments_contours.npz"
        if npz.exists() and len(mapped):
            z = np.load(npz)
            y_all, off = z["y_all"], z["offsets"]
            contours = [y_all[off[i]:off[i + 1]] for i in range(len(off) - 1)]
            ft = shape_feature_test(mapped, contours, md, a.seed)
            if len(ft):
                ft.to_csv(out / "glide_shape_feature_test.csv")
        else:
            log("skipping E (needs main_interior_wide/segments_contours.npz)")
    else:
        log("skipping D/E (needs main_interior_wide/segments.csv and fit_results.csv)")

    (out / "audit_analysis.md").write_text("\n".join(md), encoding="utf-8")
    log("\n".join(md))
    log(f"\nWrote {out}")


if __name__ == "__main__":
    main()
