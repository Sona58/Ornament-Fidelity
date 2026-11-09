# Paper map: where every reported number comes from

`<ROOT>` is the folder holding the Hindustani part of Saraga. Commands are shown for the final code release; the
`config.json` inside each result folder records the exact version, arguments and thresholds used. Run everything from
the repository root. The curated outputs live in `paper_results/` (see `paper_results/README.md`).

## 1. Regenerating the result folders

| Folder in `paper_results/` | Command | Notes |
|---|---|---|
| `main_interior_wide/` | `python scripts/01_run_reconstruction.py --saraga-root <ROOT> --out results_main --exclude-list data_lists/exclude_recordings.txt --osc-preset interior-wide --audit-glide 0 --audit-osc 40` | frozen detector; 98 recordings; then `python scripts/02_make_figures.py --results results_main` |
| `slowband_andolan/` | same with `--osc-preset andolan --audit-exclude results_main/audit_sheet.csv --out results_slow_band` | replication on 1.15-3 Hz oscillations |
| `audit_rounds/round1_default/` | `python scripts/01_run_reconstruction.py --saraga-root <ROOT> --out results_round1 --osc-preset default` | all 108 recordings (no exclusion list); default audit sizes (30 + 30) |
| `audit_rounds/round2_strict/` | `... --out results_round2 --exclude-list data_lists/exclude_recordings.txt --osc-preset strict-osc` | 98 recordings |
| `abandoned_presets/` | `... --osc-preset interior-osc` and `... --osc-preset slow-osc` | only the `results_summary.md` of each is kept (32 and 22 oscillation-like segments) |
| `sensitivity/` | `python scripts/05_sensitivity.py --saraga-root <ROOT> --out results_sens` | see note below |
| `raga/` | `python scripts/07_raga_classification.py --saraga-root <ROOT> --out results_raga --exclude-list data_lists/exclude_recordings.txt --label-map data_lists/label_map.csv --osc-preset interior-wide --perm 200` | exploratory |
| `equivalence/` | `python scripts/04_verify_cv_equivalence.py > paper_results/equivalence/cv_equivalence.txt` | needs Python >= 3.10 and PennyLane |
| `audit_analysis/` | `python scripts/08_audit_analysis.py --paper-results paper_results` | regenerates all audit-based numbers |

Audit labels are produced with `python scripts/06_audit_helper.py --results <folder>` (open `audit/index.html`, label,
download the CSV) and summarised with `--summarize <labels.csv>`. Store them with `tools/prepare_paper_results.py`.

Sensitivity note: the glide sensitivity reported in the paper was run on all 108 recordings with the detector version
that preceded the oscillation refinements. The glide detector has not changed since, so the glide ordering is
unaffected; rerun with `--exclude-list data_lists/exclude_recordings.txt` for the 98-recording version.

## 2. Paper element to output file

| Paper element | Content | File(s) |
|---|---|---|
| Table 2 | CV vs classical trajectory difference | `equivalence/cv_equivalence.txt` |
| Table 3 | detector precision (Wilson 95% CI) | glide: `audit_analysis/glide_precision.csv`; oscillation: `audit_analysis/osc_precision.csv` |
| Table 4, Figure 1 | glide reconstruction error | `main_interior_wide/summary.csv`, `aicc_winners.csv`, `paired_tests.csv`, `figures/fig_glide_examples.*` |
| Table 5 | audited-genuine glides | `audit_analysis/audited_genuine_glides.csv` |
| Table 6, Figures 2-3 | oscillation reconstruction error | `main_interior_wide/summary.csv`, `figures/fig_oscillation_examples.*`, `figures/fig_rmse_distributions.*` |
| Table 7 | error by dominant frequency | `main_interior_wide/summary_osc_by_frequency_band.csv` |
| Slow-band replication (Section 5.4) | 398 segments, 77 recordings | `slowband_andolan/summary.csv` |
| Section 5.2 | band-edge artifact, composition, bands, label-scheme effect | `audit_analysis/band_edge_artifact.csv`, `osc_composition.csv`, `osc_by_band.csv`, `osc_type_medians.csv`, `label_scheme_crosstab.csv` |
| Section 5.2 | 147 / 32 / 22 segments of abandoned presets | `audit_rounds/round2_strict/results_summary.md`, `abandoned_presets/*/results_summary.md` |
| Section 5.3 | no contour feature separates genuine glides | `audit_analysis/glide_shape_feature_test.csv` (needs contours, see below) |
| Section 5.5 | glide sensitivity (11 settings) | `sensitivity/sensitivity_median_rmse_glide.csv`, `sensitivity.csv` |
| Section 5.6, Figure 4 | precision-expressiveness descriptor | `module2_precision_expressiveness/` (see its README) |
| Table 8 | raga recognition (exploratory) | `raga/classification_results.csv`, `paired_differences.csv`, `class_counts.csv` |

`audit_analysis/glide_shape_feature_test.csv` needs `main_interior_wide/segments_contours.npz`; copy contours into
`paper_results` only if the corpus licence permits redistributing pitch contours, otherwise keep the file local.

## 3. Numbers quoted in the text, and how to recompute them

- 4,653 glide-like and 830 oscillation-like segments (85 recordings): `main_interior_wide/results_summary.md`, first line.
- Median RMSE, bootstrap CIs, IQR, recording-level means, AICc shares: `main_interior_wide/summary.csv`, `aicc_winners.csv`.
- Win rates and per-recording median differences: `main_interior_wide/paired_tests.csv` (column `segment_winrate_reference`,
  `median_rec_diff_rmse`; positive difference means the reference model is better).
- 37% and 43% reductions (hold-ramp-hold vs linear / frame snap): 1 - 15.97/25.34 and 1 - 15.97/27.98.
- 28.9-cent quantisation floor: 100 / sqrt(12).
- Fisher p = 0.25 between detectors: `audit_analysis/audit_analysis.md`, section B.
- Squeezing 1.15 and scale 32 cents implied by the mean precision and expressiveness: r = 0.5 ln(E/P), scale = sqrt(2 P E).
- Raga counts (21 of 22 etc.): accuracy x 22.
