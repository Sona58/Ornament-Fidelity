#!/usr/bin/env python
"""Manual audit of the ornament detector, made easy.

Step A (build the review page):
    python scripts\\06_audit_helper.py --results results
  -> results\\audit\\index.html  (open it in your browser)
  Each row shows the tracked contour with the fitted model, plus an audio clip cut from the real
  recording (+-1 s of context). Glide rows: Yes (a meend) / No / Unsure. Oscillation rows: Andolan /
  Kampit / Gamak / Other-or-not-an-ornament / Unsure. Then press "Download labels CSV" (audit_labels.csv).

Step B (turn the labels into detector precision with 95% CIs):
    python scripts\\06_audit_helper.py --results results --summarize "C:\\path\\to\\audit_labels.csv"

Audio needs librosa (+ffmpeg for mp3). If audio cannot be decoded the page still works (images only).
"""
import argparse
import html
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ornfid import plots  # noqa: E402  (selects the Agg backend)
from ornfid.audit import choices_html  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from ornfid.models import fit_segment  # noqa: E402
from ornfid.pipeline import load_results, log  # noqa: E402

BEST = {"glide": ("plateau_ramp", "linear"), "osc": ("sinusoid_drift", "steady_free")}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def summarize(results: Path, labels_csv: Path):
    """Precision with Wilson 95% CIs. Legacy labels yes/no are read as meend (glide) / andolan (osc).
    For oscillation rows with type labels, also reports precision for 'any oscillatory ornament'
    (andolan + kampit + gamak) and, if segments.csv is present, precision by frequency band."""
    lab = pd.read_csv(labels_csv)
    lab["label"] = lab["label"].astype(str).str.strip().str.lower()
    lab = lab[lab["label"].isin(["yes", "no", "andolan", "kampit", "gamak", "other"])].copy()
    rows = []
    g = lab[lab.ornament == "glide"]
    if len(g):
        k, n = int((g.label == "yes").sum()), len(g)
        lo, hi = wilson(k, n)
        rows.append(dict(ornament="glide", target="meend", n_labelled=n, n_yes=k, precision=k / n, ci95_lo=lo, ci95_hi=hi))
    o = lab[lab.ornament == "osc"]
    if len(o):
        k, n = int(o.label.isin(["yes", "andolan"]).sum()), len(o)
        lo, hi = wilson(k, n)
        rows.append(dict(ornament="osc", target="andolan", n_labelled=n, n_yes=k, precision=k / n, ci95_lo=lo, ci95_hi=hi))
        if o.label.isin(["kampit", "gamak", "other"]).any():
            k2 = int(o.label.isin(["andolan", "kampit", "gamak"]).sum())
            lo, hi = wilson(k2, n)
            rows.append(dict(ornament="osc", target="any oscillatory ornament", n_labelled=n, n_yes=k2,
                             precision=k2 / n, ci95_lo=lo, ci95_hi=hi))
            log("osc label counts: " + str(o.label.value_counts().to_dict()))
    out = pd.DataFrame(rows)
    out.to_csv(results / "audit_precision.csv", index=False, encoding="utf-8")
    log(out.round(3).to_string(index=False))
    segf = results / "segments.csv"
    if segf.exists() and len(o) and "freq_hz" in pd.read_csv(segf, nrows=1).columns:
        seg = pd.read_csv(segf)[["seg_id", "freq_hz", "amp_cents"]]
        m = o.merge(seg, on="seg_id")
        m["band"] = np.where(m.freq_hz <= 3.0, "<=3 Hz", ">3 Hz")
        bands = []
        for b, gg in m.groupby("band"):
            k, n = int(gg.label.isin(["yes", "andolan"]).sum()), len(gg)
            lo, hi = wilson(k, n)
            bands.append(dict(band=b, n_labelled=n, n_andolan=k, precision=k / n, ci95_lo=lo, ci95_hi=hi,
                              median_amp_cents=float(gg.amp_cents.median())))
        bd = pd.DataFrame(bands)
        bd.to_csv(results / "audit_precision_by_band.csv", index=False, encoding="utf-8")
        log("\nAndolan precision by dominant frequency:\n" + bd.round(3).to_string(index=False))
    log(f"Saved {results / 'audit_precision.csv'}  ('unsure' labels excluded)")


def build(results: Path, clip_context=1.0):
    contours, seg_meta, _res, recs = load_results(results)
    audit = pd.read_csv(results / "audit_sheet.csv")
    out = results / "audit"
    out.mkdir(exist_ok=True)
    try:
        import librosa
        from scipy.io import wavfile
        have_audio = True
    except Exception:  # noqa: BLE001
        have_audio = False
        log("librosa not available: building image-only audit page")
    rows_html, n_audio = [], 0
    for r in audit.itertuples(index=False):
        sid, kind = int(r.seg_id), r.ornament
        y = contours[sid]
        t = np.arange(len(y)) * 0.01
        preds = fit_segment(kind, y)
        fig, ax = plt.subplots(figsize=(4.4, 2.4))
        ax.plot(t, y, "k", lw=2, label="tracked f0")
        for m, c in zip(BEST[kind], ("#ff7f0e", "#3b7dd8")):
            ax.plot(t, preds[m], color=c, lw=1.2, ls="--", label=plots.LABELS[m])
        ax.set_xlabel("time (s)", fontsize=7)
        ax.set_ylabel("cents re tonic", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(out / f"seg_{sid}.png", dpi=110)
        plt.close(fig)
        audio_tag = "<i>no audio</i>"
        if have_audio:
            rec = recs[recs.rec_id == r.rec_id].iloc[0]
            if isinstance(rec.audio_file, str) and rec.audio_file:
                try:
                    off = max(0.0, float(r.t_start_abs) - clip_context)
                    sig, sr = librosa.load(rec.audio_file, sr=22050, mono=True, offset=off,
                                           duration=float(r.duration) + 2 * clip_context)
                    wavfile.write(str(out / f"seg_{sid}.wav"), sr, (np.clip(sig, -1, 1) * 32767).astype(np.int16))
                    audio_tag = (f'<audio controls preload="none" src="seg_{sid}.wav"></audio><br>'
                                 f'<small>ornament starts {min(clip_context, float(r.t_start_abs)):.1f}s into the clip, '
                                 f'lasts {float(r.duration):.2f}s</small>')
                    n_audio += 1
                except Exception as e:  # noqa: BLE001
                    audio_tag = f"<i>audio failed: {html.escape(type(e).__name__)}</i>"
        rows_html.append(
            f'<tr data-seg="{sid}" data-orn="{kind}"><td>{sid}<br><small>{r.rec_id}<br>{kind}</small></td>'
            f'<td><img src="seg_{sid}.png"></td><td>{audio_tag}</td><td>{choices_html(kind, sid)}</td></tr>')
    page = f"""<!doctype html><meta charset="utf-8"><title>Detector audit</title>
<style>body{{font-family:sans-serif;margin:16px}}td{{border-bottom:1px solid #ccc;padding:6px;vertical-align:top}}
button{{padding:8px 14px;font-size:15px}}</style>
<h2>Ornament detector audit ({len(audit)} segments)</h2>
<p>Judge from the audio and the contour whether each segment really is the named ornament. Your choices are kept in this
browser as you go; when finished press the button to save <b>audit_labels.csv</b>.</p>
<button onclick="dl()">Download labels CSV</button> <span id="cnt"></span>
<table>{''.join(rows_html)}</table>
<script>
function collect(){{var out=[["seg_id","ornament","label"]];document.querySelectorAll('tr[data-seg]').forEach(function(tr){{
 var v=tr.querySelector('input:checked');out.push([tr.dataset.seg,tr.dataset.orn,v?v.value:""]);}});return out;}}
function dl(){{var rows=collect().map(function(r){{return r.join(",")}}).join("\\n");
 var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([rows],{{type:"text/csv"}}));a.download="audit_labels.csv";a.click();}}
document.addEventListener("change",function(){{var c=collect().slice(1).filter(function(r){{return r[2]}}).length;
 document.getElementById("cnt").textContent=c+" / "+(collect().length-1)+" labelled";}});
</script>"""
    (out / "index.html").write_text(page, encoding="utf-8")
    log(f"Built {out / 'index.html'} with {len(audit)} segments ({n_audio} audio clips). Open it in your browser.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--summarize", type=Path, help="path to the downloaded audit_labels.csv")
    a = ap.parse_args()
    if a.summarize:
        summarize(a.results, a.summarize)
    else:
        build(a.results)


if __name__ == "__main__":
    main()
