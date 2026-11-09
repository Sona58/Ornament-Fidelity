#!/usr/bin/env python
"""Downstream test: do fitted ornament parameters help recognise the raga?

Per recording we build (a) a standard pitch-class distribution (PCD) baseline and (b) ornament
features from the fitted Module 1+ parameters (where glides start/end, how steep/long they are,
which notes carry oscillation and how fast/wide). We compare PCD alone vs PCD + ornament vs
ornament alone with a cross-validated, regularised classifier, report bootstrap CIs, chance and
majority baselines, and permutation p-values.

Inputs (choose one):
  --saraga-root PATH      Saraga Hindustani folder (raga from JSON metadata; groups = concerts)
  --manifest CSV          any dataset: columns rec_id, pitch_file, tonic_hz, raga [, group]
                          (pitch_file = text file with 'time  frequency' rows, 0 = unvoiced)

IMPORTANT: Saraga Hindustani has 108 recordings in ~61 ragas, so only a handful of ragas have
>= 3 recordings. The script prints exactly how many recordings/classes are usable; with so few
the result is only indicative. The CompMusic Raga Recognition Dataset (10 recordings x 30 ragas)
is far better suited; see README.

Examples:
  python scripts\\07_raga_classification.py --saraga-root "D:\\data\\saraga_hindustani" --list-labels
  python scripts\\07_raga_classification.py --saraga-root "D:\\data\\saraga_hindustani" --out results_raga
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ornfid import detect, io_saraga as io
from ornfid.models import glide_params, osc_params
from ornfid.pipeline import detect_in_runs, log, prepare_recording

EXC_BINS = [100, 200, 300, 500, 1e9]


def fold12(c):
    return np.floor(np.mod(np.asarray(c, float) + 50.0, 1200.0) / 100.0).astype(int) % 12


def hist_norm(idx, n):
    h = np.bincount(idx, minlength=n).astype(float)
    return h / h.sum() if h.sum() > 0 else h


def recording_features(prepared, voiced_s, found):
    y = np.concatenate([r for r, _ in prepared]) if prepared else np.array([])
    f = {}
    pc = np.mod(y, 1200.0)
    h12 = hist_norm(np.floor(np.mod(pc + 50, 1200) / 100).astype(int) % 12, 12)
    h24 = hist_norm(np.floor(np.mod(pc + 25, 1200) / 50).astype(int) % 24, 24)
    for i, v in enumerate(h12):
        f[f"pcd12_{i}"] = v
    for i, v in enumerate(h24):
        f[f"pcd24_{i}"] = v
    minutes = max(voiced_s / 60.0, 1e-6)
    gl = [glide_params(s["y"]) for s in found if s["ornament"] == "glide"]
    os_ = [osc_params(s["y"]) for s in found if s["ornament"] == "osc"]
    f["orn_glide_rate"] = len(gl) / minutes
    if gl:
        exc = np.array([g["end"] - g["start"] for g in gl])
        ex_h = np.histogram(np.abs(exc), bins=EXC_BINS)[0].astype(float)
        ex_h /= ex_h.sum()
        f["orn_glide_asc_frac"] = float((exc > 0).mean())
        f["orn_glide_med_dur"] = float(np.median([g["duration"] for g in gl]))
        f["orn_glide_med_rampfrac"] = float(np.median([g["ramp_frac"] for g in gl]))
        st = hist_norm(fold12([g["start"] for g in gl]), 12)
        en = hist_norm(fold12([g["end"] for g in gl]), 12)
    else:
        ex_h, st, en = np.zeros(4), np.zeros(12), np.zeros(12)
        f.update(orn_glide_asc_frac=0.0, orn_glide_med_dur=0.0, orn_glide_med_rampfrac=0.0)
    for i, v in enumerate(ex_h):
        f[f"orn_glide_exc_{i}"] = v
    for i, v in enumerate(st):
        f[f"orn_glide_start_{i}"] = v
    for i, v in enumerate(en):
        f[f"orn_glide_end_{i}"] = v
    f["orn_osc_rate"] = len(os_) / minutes
    if os_:
        f["orn_osc_med_freq"] = float(np.median([o["freq"] for o in os_]))
        f["orn_osc_med_amp"] = float(np.median([o["amp"] for o in os_]))
        f["orn_osc_med_absdrift"] = float(np.median([abs(o["drift"]) for o in os_]))
        ce = hist_norm(fold12([o["centre"] for o in os_]), 12)
    else:
        ce = np.zeros(12)
        f.update(orn_osc_med_freq=0.0, orn_osc_med_amp=0.0, orn_osc_med_absdrift=0.0)
    for i, v in enumerate(ce):
        f[f"orn_osc_centre_{i}"] = v
    f["n_glide"], f["n_osc"], f["voiced_s"] = len(gl), len(os_), voiced_s
    return f


def build_manifest(a):
    rows = []
    if a.manifest:
        m = pd.read_csv(a.manifest)
        m["raga"] = m["raga"].astype(str).map(io._norm_label)
        return m
    recs = io.find_recordings(a.saraga_root)
    recs = io.apply_lists(recs, a.saraga_root, a.include_list, a.exclude_list, a.ignore_unmatched, log)
    override = None
    if a.label_map:
        lm = pd.read_csv(a.label_map, header=None, dtype=str, keep_default_na=False)
        if len(lm) and str(lm.iloc[0, 0]).strip().lower() in ("key", "rel_key", "stem", "rec_id"):
            lm = lm.iloc[1:]                                   # optional header row
        override = {io.norm_key(str(r[0])): str(r[1]) for r in lm.itertuples(index=False)}
        log(f"label-map: {len(override)} entries")
    for r in recs:
        tonic = io.read_tonic(r)
        if tonic is None:
            log(f"[{r.rec_id}] no tonic, skipped")
            continue
        label, src = io.read_raga(r)
        if override:
            hit = override.get(io.norm_key(r.key), override.get(io.norm_key(r.rec_id)))
            if hit is not None:
                label, src = io._norm_label(hit), "label-map"
        rows.append(dict(rec_id=r.rec_id, rel_key=r.key, stem=r.stem, pitch_file=str(r.pitch_file), tonic_hz=tonic,
                         raga=label, label_source=src, group=r.folder.parent.name))
    return pd.DataFrame(rows)


def feature_sets(cols):
    pcd12 = [c for c in cols if c.startswith("pcd12_")]
    pcd24 = [c for c in cols if c.startswith("pcd24_")]
    orn = [c for c in cols if c.startswith("orn_")]
    return {"pcd12": pcd12, "pcd24": pcd24, "orn": orn, "pcd12+orn": pcd12 + orn, "pcd24+orn": pcd24 + orn}


def make_clf(name, seed):
    if name == "lr":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, class_weight="balanced", max_iter=5000))
    return RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=seed, n_jobs=1)


def predictions(X, y, groups, clf_name, mode, k, repeats, seed):
    """Return DataFrame(idx, repeat, y_true, y_pred) for every evaluated recording."""
    out = []
    n = len(y)
    if mode == "group":
        for g in np.unique(groups):
            te = np.where(groups == g)[0]
            tr = np.where(groups != g)[0]
            te = te[np.isin(y[te], np.unique(y[tr]))]          # only classes seen in training
            if len(te) == 0 or len(np.unique(y[tr])) < 2:
                continue
            clf = make_clf(clf_name, seed).fit(X[tr], y[tr])
            out += [(i, 0, y[i], p) for i, p in zip(te, clf.predict(X[te]))]
    else:
        ks = min(k, int(pd.Series(y).value_counts().min()))
        cv = RepeatedStratifiedKFold(n_splits=ks, n_repeats=repeats, random_state=seed)
        for j, (tr, te) in enumerate(cv.split(X, y)):
            clf = make_clf(clf_name, seed).fit(X[tr], y[tr])
            out += [(i, j // ks, y[i], p) for i, p in zip(te, clf.predict(X[te]))]
    return pd.DataFrame(out, columns=["idx", "repeat", "y_true", "y_pred"])


def metrics_from(pred: pd.DataFrame, idx_sample=None):
    """Mean over repeats of accuracy, balanced accuracy, macro-F1 (optionally on a bootstrap sample of recordings)."""
    if idx_sample is not None:
        w = pd.Series(idx_sample).value_counts()
        pred = pred[pred.idx.isin(w.index)].copy()
        pred["w"] = pred.idx.map(w)
    else:
        pred = pred.assign(w=1)
    res = []
    for _, g in pred.groupby("repeat"):
        correct = (g.y_true == g.y_pred).astype(float)
        acc = float((correct * g.w).sum() / g.w.sum())
        rec = g.assign(c=correct * g.w).groupby("y_true").agg(c=("c", "sum"), w=("w", "sum"))
        bal = float((rec.c / rec.w).mean())
        lab = sorted(set(g.y_true))
        f1 = f1_score(np.repeat(g.y_true.values, g.w.values.astype(int)),
                      np.repeat(g.y_pred.values, g.w.values.astype(int)), labels=lab, average="macro", zero_division=0)
        res.append((acc, bal, f1))
    return np.mean(res, axis=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--saraga-root", type=Path)
    src.add_argument("--manifest", type=Path)
    ap.add_argument("--out", type=Path, default=Path("results_raga"))
    ap.add_argument("--label-map", help="CSV (key, raga) overriding metadata labels; key = path after the Saraga root")
    ap.add_argument("--exclude-list", help="text file, one recording per line (path after the Saraga root) to skip")
    ap.add_argument("--include-list", help="same format; keep only these recordings")
    ap.add_argument("--ignore-unmatched", action="store_true")
    ap.add_argument("--min-per-raga", type=int, default=3)
    ap.add_argument("--osc-preset", choices=sorted(detect.OSC_PRESETS), default="default")
    ap.add_argument("--cv", choices=["auto", "group", "kfold"], default="auto")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--perm", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--list-labels", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    man = build_manifest(a)
    if a.manifest and a.exclude_list:
        ex = {io.norm_key(x) for x in io.read_key_list(a.exclude_list)}
        keycol = man["rel_key"] if "rel_key" in man else man["rec_id"]
        man = man[~(keycol.map(io.norm_key).isin(ex) | man["rec_id"].map(io.norm_key).isin(ex))]
    counts = man.groupby("raga").agg(n_recordings=("rec_id", "size"),
                                     n_groups=("group", "nunique") if "group" in man else ("rec_id", "size"))
    counts = counts.sort_values("n_recordings", ascending=False)
    counts.to_csv(a.out / "class_counts.csv", encoding="utf-8")
    man.to_csv(a.out / "manifest_used.csv", index=False, encoding="utf-8")
    elig = counts[counts.n_recordings >= a.min_per_raga]
    log(f"{len(man)} recordings, {len(counts)} distinct raga labels; label sources: "
        f"{man.get('label_source', pd.Series(['manifest'])).value_counts().to_dict()}")
    log(f"Ragas with >= {a.min_per_raga} recordings: {len(elig)} classes covering {int(elig.n_recordings.sum())} recordings")
    log(counts.head(15).to_string())
    if a.list_labels:
        return
    if len(elig) < 2:
        log("Fewer than 2 usable raga classes: classification would be meaningless. Use a larger / balanced "
            "dataset (see README: CompMusic Raga Recognition Dataset) or lower --min-per-raga.")
        return
    man = man[man.raga.isin(elig.index)].reset_index(drop=True)

    feat_path = a.out / "features.csv"
    feats = []
    for k, r in man.iterrows():
        t, f0 = io.read_pitch(Path(r.pitch_file))
        prepared, voiced_s = prepare_recording(t, f0, float(r.tonic_hz))
        found = detect_in_runs(prepared, None, detect.OSC_PRESETS[a.osc_preset])
        feats.append(recording_features(prepared, voiced_s, found))
        log(f"features {k + 1}/{len(man)} {r.rec_id} glides={feats[-1]['n_glide']} osc={feats[-1]['n_osc']}")
    F = pd.concat([man.reset_index(drop=True), pd.DataFrame(feats)], axis=1)
    F.to_csv(feat_path, index=False, encoding="utf-8")

    y = F.raga.values
    groups = F["group"].values if "group" in F else None
    mode = a.cv
    if mode == "auto":
        mode = "group" if groups is not None and len(np.unique(groups)) >= 3 else "kfold"
    sets = feature_sets(list(F.columns))
    rng = np.random.default_rng(a.seed)
    rows, store = [], {}
    for clf_name in ("lr", "rf"):
        for fs, cols in sets.items():
            X = F[cols].values.astype(float)
            pred = predictions(X, y, groups, clf_name, mode, a.k, a.repeats, a.seed)
            store[(clf_name, fs)] = pred
    ev_idx = np.unique(store[("lr", "pcd24")].idx)
    maj = pd.Series(y[ev_idx]).value_counts(normalize=True).iloc[0]
    chance = 1.0 / len(np.unique(y[ev_idx]))
    boots = [rng.choice(ev_idx, size=len(ev_idx), replace=True) for _ in range(a.boot)]
    for (clf_name, fs), pred in store.items():
        acc, bal, f1 = metrics_from(pred)
        bs = np.array([metrics_from(pred, b) for b in boots])
        lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        row = dict(clf=clf_name, features=fs, n_eval=len(ev_idx), n_classes=len(np.unique(y[ev_idx])),
                   acc=acc, acc_lo=lo[0], acc_hi=hi[0], bal_acc=bal, bal_lo=lo[1], bal_hi=hi[1],
                   macro_f1=f1, f1_lo=lo[2], f1_hi=hi[2], majority_acc=maj, chance_acc=chance)
        if clf_name == "lr" and a.perm > 0:
            X = F[sets[fs]].values.astype(float)
            null = []
            for _ in range(a.perm):
                yp = rng.permutation(y)
                pp = predictions(X, yp, groups, "lr", mode, a.k, 1, a.seed)
                null.append(metrics_from(pp)[0])
            row["perm_p_acc"] = float((1 + np.sum(np.array(null) >= acc)) / (1 + a.perm))
        rows.append(row)
    res = pd.DataFrame(rows)
    res.to_csv(a.out / "classification_results.csv", index=False, encoding="utf-8")

    # paired bootstrap: does adding ornament features change accuracy over PCD alone?
    diffs = []
    for clf_name in ("lr", "rf"):
        for base in ("pcd12", "pcd24"):
            pa, pb = store[(clf_name, base)], store[(clf_name, base + "+orn")]
            d = np.array([metrics_from(pb, b)[0] - metrics_from(pa, b)[0] for b in boots])
            diffs.append(dict(clf=clf_name, comparison=f"{base}+orn minus {base}",
                              acc_diff=metrics_from(pb)[0] - metrics_from(pa)[0],
                              ci_lo=np.percentile(d, 2.5), ci_hi=np.percentile(d, 97.5)))
    dd = pd.DataFrame(diffs)
    dd.to_csv(a.out / "paired_differences.csv", index=False, encoding="utf-8")
    cfg = dict(args={k: str(v) for k, v in vars(a).items()}, cv_mode=mode, n_recordings=len(F),
               n_eval=int(len(ev_idx)), n_classes=int(len(np.unique(y[ev_idx]))))
    (a.out / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    log(f"\nCV mode: {mode};  evaluated recordings: {len(ev_idx)} in {cfg['n_classes']} ragas; "
        f"majority-class acc = {maj:.3f}; chance = {chance:.3f}")
    log(res.round(3).to_string(index=False))
    log("\nPaired differences (ornament features added to PCD):")
    log(dd.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
