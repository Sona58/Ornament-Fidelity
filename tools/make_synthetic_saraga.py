#!/usr/bin/env python
"""Create a tiny *synthetic* Saraga-like folder tree (NOT real data) to smoke-test the
pipeline and your installation:  python tools/make_synthetic_saraga.py --out synth_saraga
then:  python scripts/01_run_reconstruction.py --saraga-root synth_saraga --out results_synth
"""
import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile


RAGAS = {"Alpha": dict(swar=[0, 200, 400, 700, 900], osc=400),
         "Beta": dict(swar=[0, 100, 300, 500, 700, 800], osc=300),
         "Gamma": dict(swar=[0, 200, 300, 500, 700, 1000], osc=700)}


def make_track(rng, tonic, dur=120.0, hop=128 / 44100, raga="Alpha"):
    cfg = RAGAS[raga]
    t = np.arange(0, dur, hop)
    cents = np.zeros_like(t)
    cur, i = 0.0, 0
    swar = np.array(cfg['swar'], float) + rng.choice([-10, 0, 10], len(cfg['swar']))
    voiced = np.ones_like(t, bool)
    while i < len(t):
        kind = rng.choice(["hold", "glide", "osc", "gap"], p=[.3, .3, .3, .1])
        n = int(rng.uniform(0.8, 3.0) / hop)
        j = min(len(t), i + n)
        tt = (np.arange(j - i)) * hop
        if kind == "hold":
            cents[i:j] = cur + rng.normal(0, 5)
        elif kind == "glide":
            tgt = float(rng.choice(swar))
            u = np.linspace(0, 1, j - i)
            cents[i:j] = cur + (tgt - cur) * (1 - np.cos(np.pi * u)) / 2
            cur = tgt
        elif kind == "osc":
            if rng.random() < 0.7:
                cur = float(cfg["osc"])
            cents[i:j] = cur + rng.uniform(25, 70) * np.sin(2 * np.pi * rng.uniform(2, 4.5) * tt)
        else:
            cents[i:j] = cur
            voiced[i:j] = False
        i = j
    cents += rng.normal(0, 4, len(t))
    f0 = tonic * 2 ** (cents / 1200)
    f0[~voiced] = 0.0
    return t, f0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("synth_saraga"))
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--audio", action="store_true", help="also write a wav so --spectrograms can be tested")
    a = ap.parse_args()
    rng = np.random.default_rng(1)
    names = list(RAGAS)
    for k in range(a.n):
        raga = names[k % 3]
        stem = f"Raag {raga} take {k // 3 + 1}"
        d = a.out / f"Concert {k // 3 + 1}" / stem
        d.mkdir(parents=True, exist_ok=True)
        tonic = float(rng.uniform(120, 200))
        t, f0 = make_track(rng, tonic, raga=raga)
        np.savetxt(d / f"{stem}.pitch.txt", np.column_stack([t, f0]), fmt="%.6f", delimiter="\t")
        (d / f"{stem}.ctonic").write_text(f"{tonic:.3f}\n")
        import json
        (d / f"{stem}.json").write_text(json.dumps({"raags": [{"name": raga, "common_name": raga}]}))
        if a.audio:
            sr = 22050
            tt = np.arange(int(t[-1] * sr)) / sr
            f = np.interp(tt, t, np.where(f0 > 0, f0, 1.0))
            w = 0.3 * np.sin(2 * np.pi * np.cumsum(f) / sr)
            wavfile.write(str(d / f"{stem}.mp3.wav"), sr, (w * 32767).astype(np.int16))
    print(f"Wrote {a.n} synthetic tracks to {a.out}")


if __name__ == "__main__":
    main()
