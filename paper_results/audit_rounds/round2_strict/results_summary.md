# Reconstruction results (RMSE in cents, lower = better)

Recordings used: 98; segments: 4800 (4653 glide-like, 147 oscillation-like).

Segments are *detected by signal heuristics*, not human-annotated; see audit_sheet.csv.

## Per-model summary

| ornament | model | n_segments | rmse_median | rmse_median_ci_lo | rmse_median_ci_hi | rmse_q25 | rmse_q75 | rec_level_rmse_mean |
|---|---|---|---|---|---|---|---|---|
| glide | tet12_notes | 4653 | 124.00 | 120.78 | 126.65 | 85.36 | 178.92 | 143.20 |
| glide | shruti22_notes | 4653 | 122.13 | 119.51 | 125.55 | 85.81 | 178.73 | 142.78 |
| glide | tet12_framesnap | 4653 | 27.98 | 27.88 | 28.05 | 26.36 | 29.46 | 27.83 |
| glide | linear | 4653 | 25.34 | 24.78 | 25.98 | 15.21 | 41.26 | 34.12 |
| glide | cosine_module1 | 4653 | 28.54 | 27.90 | 29.23 | 17.21 | 46.11 | 37.86 |
| glide | plateau_ramp | 4653 | 15.97 | 15.58 | 16.30 | 10.53 | 25.42 | 20.89 |
| glide | plateau_cosine | 4653 | 21.03 | 20.60 | 21.63 | 13.55 | 33.38 | 26.24 |
| osc | tet12_note | 147 | 58.00 | 54.89 | 60.37 | 49.86 | 67.28 | 61.62 |
| osc | shruti22_note | 147 | 55.43 | 52.77 | 57.37 | 47.17 | 66.31 | 58.96 |
| osc | tet12_framesnap | 147 | 21.71 | 21.04 | 22.72 | 19.09 | 24.67 | 22.16 |
| osc | steady_free | 147 | 45.77 | 43.07 | 47.96 | 39.41 | 59.99 | 52.27 |
| osc | linear_drift | 147 | 43.86 | 41.72 | 47.21 | 35.20 | 57.12 | 49.15 |
| osc | sinusoid_module1 | 147 | 30.47 | 28.61 | 32.52 | 23.02 | 39.84 | 35.71 |
| osc | sinusoid_drift | 147 | 25.24 | 23.22 | 27.76 | 20.15 | 35.85 | 30.14 |


## Complexity-penalised comparison (share of segments where each parametric model has the lowest AICc)

| ornament | model | share_best_aicc |
|---|---|---|
| glide | linear | 0.501 |
| glide | cosine_module1 | 0.111 |
| glide | plateau_ramp | 0.300 |
| glide | plateau_cosine | 0.088 |
| osc | steady_free | 0.000 |
| osc | linear_drift | 0.000 |
| osc | sinusoid_module1 | 0.272 |
| osc | sinusoid_drift | 0.728 |


## Paired recording-level tests vs each reference model (Holm-corrected; diff>0 = reference better)

| ornament | baseline | reference | n_recordings | median_rec_diff_rmse | segment_winrate_reference | wilcoxon_p | p_holm |
|---|---|---|---|---|---|---|---|
| glide | linear | cosine_module1 | 98 | -3.592 | 0.2179 | 7.001e-16 | 1.4e-15 |
| glide | plateau_cosine | cosine_module1 | 98 | -10.83 | 0.0677 | 8.33e-18 | 4.998e-17 |
| glide | plateau_ramp | cosine_module1 | 98 | -15.96 | 0.03589 | 8.33e-18 | 4.998e-17 |
| glide | shruti22_notes | cosine_module1 | 98 | 103.1 | 1 | 8.33e-18 | 4.998e-17 |
| glide | tet12_framesnap | cosine_module1 | 98 | -8.603 | 0.4788 | 6.076e-13 | 6.076e-13 |
| glide | tet12_notes | cosine_module1 | 98 | 103.6 | 1 | 8.33e-18 | 4.998e-17 |
| glide | cosine_module1 | plateau_cosine | 98 | 10.83 | 0.8777 | 8.33e-18 | 4.998e-17 |
| glide | linear | plateau_cosine | 98 | 7.139 | 0.5878 | 2.915e-16 | 5.829e-16 |
| glide | plateau_ramp | plateau_cosine | 98 | -5.042 | 0.1661 | 8.33e-18 | 4.998e-17 |
| glide | shruti22_notes | plateau_cosine | 98 | 114.7 | 1 | 8.33e-18 | 4.998e-17 |
| glide | tet12_framesnap | plateau_cosine | 98 | 2.518 | 0.6579 | 0.001401 | 0.001401 |
| glide | tet12_notes | plateau_cosine | 98 | 116.1 | 1 | 8.33e-18 | 4.998e-17 |
| osc | linear_drift | sinusoid_module1 | 43 | 14.19 | 0.9184 | 2.274e-13 | 1.364e-12 |
| osc | shruti22_note | sinusoid_module1 | 43 | 23.72 | 1 | 2.274e-13 | 1.364e-12 |
| osc | sinusoid_drift | sinusoid_module1 | 43 | -3.954 | 0 | 2.274e-13 | 1.364e-12 |
| osc | steady_free | sinusoid_module1 | 43 | 16.57 | 1 | 2.274e-13 | 1.364e-12 |
| osc | tet12_framesnap | sinusoid_module1 | 43 | -13.17 | 0.1837 | 4.707e-11 | 4.707e-11 |
| osc | tet12_note | sinusoid_module1 | 43 | 25.34 | 1 | 2.274e-13 | 1.364e-12 |
| osc | linear_drift | sinusoid_drift | 43 | 19.03 | 1 | 2.274e-13 | 1.364e-12 |
| osc | shruti22_note | sinusoid_drift | 43 | 28.36 | 1 | 2.274e-13 | 1.364e-12 |
| osc | sinusoid_module1 | sinusoid_drift | 43 | 3.954 | 1 | 2.274e-13 | 1.364e-12 |
| osc | steady_free | sinusoid_drift | 43 | 21.72 | 1 | 2.274e-13 | 1.364e-12 |
| osc | tet12_framesnap | sinusoid_drift | 43 | -8.086 | 0.3061 | 9.077e-07 | 9.077e-07 |
| osc | tet12_note | sinusoid_drift | 43 | 32.21 | 1 | 2.274e-13 | 1.364e-12 |