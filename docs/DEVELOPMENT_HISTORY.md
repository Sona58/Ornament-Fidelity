# Development history of the detectors and audits

The detectors were refined over several audit rounds. This file records the sequence so that the final detector is not
mistaken for a pre-specified one. All audits were done by a single annotator; every round after the first sampled
segments not used in earlier rounds (`--audit-exclude`). The `config.json` of each result folder is authoritative for
the code version and thresholds used.

## Code versions

| Version | Change that mattered for results |
|---|---|
| 0.1 | first reconstruction pipeline. All tonics were estimated because the corpus stores tonics in `.ctonic` files, which the reader did not look for; tested to be double-sure on the tonics; **those results are invalid and are not part of the paper** |
| 0.2 | reads `.ctonic`, refuses to run on estimated tonics; hold-ramp-hold glide models, drift-aware oscillation models, frame-snap baseline, AICc, glide boundary extension into low-slope shoulders, sensitivity script |
| 0.3 | audit page (contour + audio clip + labels), `--summarize`; equivalence script extended to the hold-ramp-hold path and the drifting sinusoid |
| 0.4 | raga-recognition script; `strict-osc` preset; parameter extractors |
| 0.4.1 | include/exclude lists and label maps keyed by path relative to the corpus root |
| 0.5.0 | band-edge fix: `interior-osc` and `slow-osc` presets |
| 0.5.1 | `interior-wide` preset (original thresholds and band, band-edge rule only); audit sizes per class; frequency-band table |
| 0.6.0 | `andolan` preset (1.15-3 Hz); `--audit-exclude`. The four-way labels were announced but **not actually added to the audit page** (a text replacement silently failed) |
| 0.6.1 | fixes the audit page; a test now inspects the generated HTML |
| 1.0.0 | release: audit-analysis script, result-preparation tool, documentation |

## Audit rounds

| Round | Detector / data | Labels | Result |
|---|---|---|---|
| 1 | `default` oscillation detector, all 108 recordings | yes/no | glide 21/29 genuine; oscillation 11/25. 64% of oscillation-like detections had their spectral peak at the lowest band bin (about 1.03 Hz): slow wander, not oscillation |
| 2 | `strict-osc`, 98 recordings (4,653 glide-like, 147 oscillation-like from 43 recordings) | yes/no | glide 20/29; oscillation 19/28. All 9 "not genuine" oscillation segments had band-edge peaks; all 7 interior-peak segments were genuine; 76% of detections were edge-pinned |
| - | `interior-osc` (32 segments, 13 recordings) and `slow-osc` (22 segments, 13 recordings) | not audited | too few segments; abandoned |
| 3 | `interior-wide` (830 oscillation-like, 85 recordings) | yes/no | 23/39 "andolan"; at or below 3 Hz 20/22, above 3 Hz 3/17 |
| 4 | `andolan` preset (398 oscillation-like, 77 recordings), fresh sample | yes/no | 21/40: the 3 Hz cut chosen from round 3 did not confirm |
| 5 | rounds 3 and 4 relabelled with the four-way scheme (andolan / kampit / gamak / other) | four-way | interior-wide: 35/40 any oscillatory ornament (14 andolan, 13 kampit, 8 gamak, 5 other); andolan preset: 30/39 (15 andolan, 9 gamak, 9 other, 6 kampit) |

Observations that shaped the final design:

- The same segments were called genuine andolan more often under yes/no than under the four-way scheme (of 21 yes/no
  "genuine" slow-band segments, 13 became andolan, 5 gamak, 2 kampit, 1 other), so oscillation-type ornaments are
  treated as one class and the finer categories are not claimed.
- The detector was frozen at `interior-wide` (higher point precision for any oscillatory ornament and a larger sample).
  The choice was informed by the audit, so its precision may be slightly optimistic; the two intervals overlap
  (Fisher p = 0.25).
- No contour-shape feature (17 tested, n = 56 audited glides) separated genuine from non-genuine glide detections better
  than chance (max |AUC - 0.5| = 0.15 against a permutation 95th percentile of 0.24).
- On the 40 audited-genuine glides the model ranking matched the full-corpus ranking (Spearman 0.96).

## Raga-recognition test

Labels come from corpus metadata (88 recordings), the track name (10 recordings from releases in which two ragas share a
release) and two recordings relabelled from `bhimpalas` to `bhimpalasi` (a spelling variant of the same raga, `data_lists/label_map.csv`). Only ragas with at
least three recordings are used: six ragas, 22 recordings. No features or hyperparameters were tuned.
