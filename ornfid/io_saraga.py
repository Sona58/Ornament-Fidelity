"""Locate and read Saraga (Hindustani) files from a local copy of the dataset.

Expected layout (Saraga 1.5, as distributed on Zenodo / mirdata):

    <root>/<concert folder>/<track folder>/<stem>.pitch-vocal.txt   (preferred)
                                          /<stem>.pitch.txt
                                          /<stem>.tonic.txt          (if present)
                                          /<stem>.multitrack-vocal.mp3 | <stem>.mp3.mp3 ...

The reader is deliberately tolerant: it groups files by (folder, stem), so it
also works if the nesting differs slightly. Run `scripts/01_run_reconstruction.py
--list-only` to see exactly what was found before running anything heavy.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

_PITCH_RE = re.compile(r"^(?P<stem>.+)\.(?P<kind>pitch-vocal|pitch)\.txt$", re.IGNORECASE)
_PREFERENCE = {"pitch-vocal": 0, "pitch": 1}


@dataclass
class Recording:
    rec_id: str
    stem: str
    folder: Path
    pitch_file: Path
    pitch_kind: str
    tonic_file: Optional[Path]
    audio_file: Optional[Path]
    rel_folder: str = ""   # release/raag folder relative to the Saraga root, '/'-separated
    key: str = ""          # rel_folder + '/' + stem  -> unique, human-readable recording identifier


def _find_audio(folder: Path, stem: str) -> Optional[Path]:
    candidates = [
        f"{stem}.multitrack-vocal.mp3", f"{stem}.multitrack-vocal.wav",
        f"{stem}.mp3.mp3", f"{stem}.mp3", f"{stem}.wav",
    ]
    for name in candidates:
        p = folder / name
        if p.exists():
            return p
    for p in sorted(folder.glob("*.mp3")) + sorted(folder.glob("*.wav")):
        return p
    return None


def _find_tonic(folder: Path, stem: str) -> Optional[Path]:
    """Saraga stores the tonic as <stem>.ctonic (plain text, Hz); also accept .ctonic.txt / .tonic.txt."""
    for name in (f"{stem}.ctonic", f"{stem}.ctonic.txt", f"{stem}.tonic.txt", f"{stem}.tonic"):
        p = folder / name
        if p.exists():
            return p
    for pat in ("*.ctonic", "*.ctonic.txt", "*.tonic.txt", "*.tonic"):
        hits = sorted(folder.glob(pat))
        if hits:
            return hits[0]
    return None


def find_recordings(root: Path) -> list[Recording]:
    """Return one Recording per (folder, stem), choosing the best pitch file."""
    root = Path(root)
    best: dict[tuple[Path, str], tuple[int, Path, str]] = {}
    for p in root.rglob("*.txt"):
        m = _PITCH_RE.match(p.name)
        if not m:
            continue
        key = (p.parent, m.group("stem"))
        kind = m.group("kind").lower()
        rank = _PREFERENCE[kind]
        if key not in best or rank < best[key][0]:
            best[key] = (rank, p, kind)
    recs: list[Recording] = []
    for i, ((folder, stem), (_, pfile, kind)) in enumerate(sorted(best.items(), key=lambda kv: str(kv[0]))):
        try:
            rel = folder.relative_to(root).as_posix()
        except ValueError:
            rel = folder.name
        rel = "" if rel == "." else rel
        recs.append(Recording(
            rec_id=f"R{i + 1:03d}", stem=stem, folder=folder, pitch_file=pfile,
            pitch_kind=kind, tonic_file=_find_tonic(folder, stem),
            audio_file=_find_audio(folder, stem), rel_folder=rel,
            key=f"{rel}/{stem}" if rel else stem))
    return recs


def read_pitch(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a Saraga pitch file -> (time_s, f0_hz). Unvoiced frames have f0 <= 0."""
    path = Path(path)
    try:
        arr = np.loadtxt(path, dtype=float, ndmin=2)
    except ValueError:
        rows = []
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                parts = [x for x in re.split(r"[\s,;]+", line.strip()) if x]
                if len(parts) >= 2:
                    try:
                        rows.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        continue
        arr = np.asarray(rows, dtype=float)
    if arr.ndim != 2 or arr.shape[1] < 2 or arr.shape[0] < 10:
        raise ValueError(f"Unrecognised pitch file format: {path}")
    t, f = arr[:, 0], arr[:, 1]
    order = np.argsort(t)
    return t[order], f[order]


def read_tonic(rec: Recording) -> Optional[float]:
    """Tonic in Hz from <stem>.tonic.txt, else from a 'tonic' key in the JSON metadata."""
    if rec.tonic_file is not None:
        try:
            txt = Path(rec.tonic_file).read_text(encoding="utf-8", errors="ignore")
            nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", txt)
            if nums:
                val = float(nums[0])
                if 50 < val < 600:
                    return val
        except OSError:
            pass
    meta = rec.folder / f"{rec.stem}.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8", errors="ignore"))
            val = _search_key(data, "tonic")
            if isinstance(val, (int, float)) and 50 < val < 600:
                return float(val)
        except (OSError, json.JSONDecodeError):
            pass
    return None


def _search_key(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == key:
                return v
            r = _search_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _search_key(v, key)
            if r is not None:
                return r
    return None


def estimate_tonic_from_histogram(f0_hz: np.ndarray) -> float:
    """Fallback only: strongest folded-octave pitch-histogram peak (logged as 'estimated')."""
    f = f0_hz[(f0_hz > 60) & (f0_hz < 1000)]
    ref = 55.0
    cents = np.mod(1200 * np.log2(f / ref), 1200)
    hist, edges = np.histogram(cents, bins=240, range=(0, 1200))
    peak_c = edges[np.argmax(hist)] + 2.5
    # place tonic in 100-250 Hz range (typical vocal tonic range)
    base = ref * 2 ** (peak_c / 1200)
    while base < 100:
        base *= 2
    while base > 250:
        base /= 2
    return float(base)


def _norm_label(x: str) -> str:
    x = re.sub(r"[^a-z0-9 ]+", " ", x.lower())
    x = re.sub(r"^(raag|raga|rag)\s+", "", x.strip())
    return re.sub(r"\s+", " ", x).strip()


def read_raga(rec: Recording):
    """Raga label of a Saraga recording -> (normalised_label, source). Uses the JSON metadata
    ('raags' list, or a 'raag'/'raga' string); falls back to the track/folder name."""
    meta = rec.folder / f"{rec.stem}.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8", errors="ignore"))
            for key in ("raags", "raag", "raga"):
                val = _search_key(data, key)
                name = None
                if isinstance(val, list) and val:
                    v0 = val[0]
                    name = (v0.get("common_name") or v0.get("name")) if isinstance(v0, dict) else str(v0)
                elif isinstance(val, dict):
                    name = val.get("common_name") or val.get("name")
                elif isinstance(val, str):
                    name = val
                if name:
                    return _norm_label(str(name)), "json"
        except (OSError, json.JSONDecodeError):
            pass
    return _norm_label(rec.stem), "stem"


# ---------------------------------------------------------------------------------------------
# Include / exclude lists keyed by path relative to the Saraga root
# ---------------------------------------------------------------------------------------------
_KNOWN_SUFFIXES = (".pitch-vocal.txt", ".pitch.txt", ".ctonic.txt", ".ctonic", ".tonic.txt", ".tonic",
                   ".mp3.mp3", ".multitrack-vocal.mp3", ".mp3", ".wav", ".json", ".txt")


def norm_key(text: str) -> str:
    """Normalise a path-like key: strip quotes/whitespace, unify slashes (Windows or POSIX), drop a known
    file suffix, case-fold. 'Release\\Raag X\\Raag X.pitch.txt' -> 'release/raag x/raag x'."""
    t = str(text).strip().strip('"').strip("'").replace("\\", "/")
    t = re.sub(r"/+", "/", t).strip("/")
    low = t.lower()
    for suf in _KNOWN_SUFFIXES:
        if low.endswith(suf):
            t = t[: -len(suf)]
            break
    return t.casefold()


def read_key_list(path) -> list:
    """One entry per line; blank lines and lines starting with '#' are ignored."""
    lines = Path(path).read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def resolve_keys(recs, entries, root):
    """Match list entries to recordings. An entry may be: the full key 'release/raag/stem' (recommended;
    with or without a file extension, any slash style, or an absolute path under the root), a folder path
    'release/raag', a rec_id ('R012'), or a bare stem (accepted only if it is unique).
    Returns (matched_rec_ids, unmatched_entries, ambiguous_entries[(entry, [candidate keys])])."""
    root_n = norm_key(str(root))
    by_key, by_folder, by_stem, by_id = {}, {}, {}, {}
    for r in recs:
        by_key.setdefault(norm_key(r.key), []).append(r)
        if r.rel_folder:
            by_folder.setdefault(norm_key(r.rel_folder), []).append(r)
        by_stem.setdefault(norm_key(r.stem), []).append(r)
        by_id[r.rec_id.casefold()] = [r]
    matched, unmatched, ambiguous = set(), [], []
    for entry in entries:
        k = norm_key(entry)
        if k.startswith(root_n + "/"):
            k = k[len(root_n) + 1:]
        hits = by_key.get(k) or by_folder.get(k) or by_id.get(k)
        if hits is None:
            hits = by_stem.get(k)
            if hits is not None and len(hits) > 1:
                ambiguous.append((entry, [h.key for h in hits]))
                continue
        if hits is None:
            unmatched.append(entry)
        else:
            matched.update(h.rec_id for h in hits)
    return matched, unmatched, ambiguous


def apply_lists(recs, root, include_path=None, exclude_path=None, ignore_unmatched=False, log=print):
    """Filter recordings by include/exclude lists; stop (SystemExit) on unmatched or ambiguous entries
    unless ignore_unmatched is set, so a typo can never silently leave a recording in the analysis."""
    problems = False
    for label, path in (("include", include_path), ("exclude", exclude_path)):
        if not path:
            continue
        entries = read_key_list(path)
        matched, unmatched, ambiguous = resolve_keys(recs, entries, root)
        log(f"{label}-list: {len(entries)} entries -> {len(matched)} recordings matched")
        for e in unmatched:
            log(f"  NO MATCH: {e}")
        for e, cands in ambiguous:
            log(f"  AMBIGUOUS bare name {e!r}; use the full path. Candidates:")
            for c in cands:
                log(f"      {c}")
        problems = problems or bool(unmatched or ambiguous)
        recs = [r for r in recs if (r.rec_id in matched) == (label == "include")]
    if problems and not ignore_unmatched:
        raise SystemExit("Fix the entries above (or pass --ignore-unmatched). Run with --list-only --write-keys "
                         "all_keys.txt to get the exact key of every recording.")
    return recs
