# Ornament Fidelity: continuous trajectory models for Hindustani ornaments

Code accompanying the paper *Continuous Trajectory Models for Hindustani Ornaments: Reconstruction Fidelity of Glide and
Oscillation Alankaars on the Saraga Corpus*. It measures how closely compact parametric trajectories,
expressed as continuous-variable (CV) displacement and rotation operations, reproduce the tracked pitch contour of
glide-type and oscillation-type ornaments, compared with note-level, grid-based and classical baselines.

> **Scope.** The CV trajectories equal their classical formulas to machine precision (`scripts/04`), so nothing here
> needs quantum hardware, and no quantum advantage is claimed. Ornament segments are found by signal heuristics, not
> expert annotation; detector precision was estimated by a single-annotator audit (see `docs/DEVELOPMENT_HISTORY.md`).

## Install
```
python -m venv .venv && .venv\Scripts\activate        (Windows;  source .venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
python -m pytest tests -q
```
`librosa` (+ `ffmpeg` on PATH for mp3) is only needed for the audit audio clips and spectrograms. `pennylane` is only
needed for `scripts/04` and requires Python >= 3.10.

## Quick start
The Saraga corpus is **not** included; obtain it under its own licence. Recordings are identified by their path after the
corpus root, `<release folder>\<raag folder>\<recording name>`, which keeps names unique across releases.
```
python scripts/01_run_reconstruction.py --saraga-root <ROOT> --list-only --write-keys all_keys.txt   # check discovery, get keys
python scripts/01_run_reconstruction.py --saraga-root <ROOT> --out results --exclude-list data_lists/exclude_recordings.txt --osc-preset interior-wide
python scripts/02_make_figures.py --results results
python scripts/03_render_audio_samples.py --results results      # synthetic-timbre audio of contour vs models
```
| Script | Purpose |
|---|---|
| `01_run_reconstruction.py` | find recordings and tonics, preprocess, detect ornaments, fit all models, statistics, audit sheet |
| `02_make_figures.py` | example overlays and error distributions (`--spectrograms` needs audio) |
| `03_render_audio_samples.py` | synthetic audio for inspection |
| `04_verify_cv_equivalence.py` | CV (PennyLane) vs classical trajectories |
| `05_sensitivity.py` | glide ranking under 11 detector settings |
| `06_audit_helper.py` | browser audit page; `--summarize` gives precision with Wilson CIs |
| `07_raga_classification.py` | exploratory raga recognition, pitch-class baseline vs ornament parameters |
| `08_audit_analysis.py` | reproduces every audit-based number in the paper from `paper_results/` |
| `tools/prepare_paper_results.py` | copies only shareable outputs into `paper_results/` |

## Oscillation detector presets
| `--osc-preset` | Description |
|---|---|
| `default` | 1-6.5 Hz band, no edge rule (shows the band-edge artifact; kept for the record) |
| `strict-osc`, `interior-osc`, `slow-osc` | stricter variants that kept 147, 32 and 22 segments; abandoned |
| **`interior-wide`** | **final**: default thresholds plus peak >= 0.15 Hz inside the band and no stronger component below 1 Hz |
| `andolan` | 1.15-3 Hz replication |

## Include / exclude lists
One recording per line as `<release>\<raag>\<name>`; any slash style, case, quotes, a file extension or an absolute path
under the root are accepted, as is an `R###` id; a bare name only if unique. The scripts stop on an entry that matches
nothing or is ambiguous (override with `--ignore-unmatched`).

## Audit workflow
`python scripts/06_audit_helper.py --results <folder>` builds `<folder>/audit/index.html` (contour, fitted models, a clip
of the recording). Label every row (glides: yes / no / unsure; oscillations: andolan / kampit / gamak / other / unsure),
download the CSV, then `... --summarize <labels.csv>`. Audio clips come from the corpus; do not commit them.

## Reproducing the paper
`docs/PAPER_MAP.md` maps every table, figure and quoted number to a command and an output file.
`docs/DEVELOPMENT_HISTORY.md` records the detector refinements and audit rounds.

## Data and licences
Code: MIT (see `LICENSE`). Saraga is not redistributed; check its terms before sharing derived pitch data or audio, and
keep the audio clips, review pages and spectrograms out of the repository (`.gitignore` excludes them).

## Citation
See `CITATION.cff` (GitHub shows a "Cite this repository" button). Cite the archived release DOI [add Zenodo DOI].
