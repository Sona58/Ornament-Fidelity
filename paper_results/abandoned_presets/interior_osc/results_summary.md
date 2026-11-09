# Reconstruction results (RMSE in cents, lower = better)

Recordings used: 98; segments: 4685 (4653 glide-like, 32 oscillation-like).

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
| osc | tet12_note | 32 | 62.23 | 56.58 | 65.85 | 54.26 | 67.47 | 65.43 |
| osc | shruti22_note | 32 | 59.27 | 55.43 | 61.53 | 52.75 | 62.38 | 61.48 |
| osc | tet12_framesnap | 32 | 20.90 | 17.13 | 23.49 | 16.04 | 25.23 | 21.87 |
| osc | steady_free | 32 | 44.15 | 41.69 | 47.96 | 41.44 | 57.63 | 52.15 |
| osc | linear_drift | 32 | 42.44 | 41.24 | 47.49 | 40.39 | 53.70 | 49.94 |
| osc | sinusoid_module1 | 32 | 28.82 | 22.72 | 32.29 | 22.00 | 39.03 | 33.84 |
| osc | sinusoid_drift | 32 | 26.18 | 21.99 | 30.87 | 20.34 | 34.69 | 31.12 |


## Complexity-penalised comparison (share of segments where each parametric model has the lowest AICc)

| ornament | model | share_best_aicc |
|---|---|---|
| glide | linear | 0.501 |
| glide | cosine_module1 | 0.111 |
| glide | plateau_ramp | 0.300 |
| glide | plateau_cosine | 0.088 |
| osc | steady_free | 0.000 |
| osc | linear_drift | 0.000 |
| osc | sinusoid_module1 | 0.250 |
| osc | sinusoid_drift | 0.750 |


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
| osc | linear_drift | sinusoid_module1 | 13 | 17.2 | 1 | 0.0002441 | 0.001465 |
| osc | shruti22_note | sinusoid_module1 | 13 | 28.18 | 1 | 0.0002441 | 0.001465 |
| osc | sinusoid_drift | sinusoid_module1 | 13 | -2.519 | 0 | 0.0002441 | 0.001465 |
| osc | steady_free | sinusoid_module1 | 13 | 18.99 | 1 | 0.0002441 | 0.001465 |
| osc | tet12_framesnap | sinusoid_module1 | 13 | -9.295 | 0.2188 | 0.001221 | 0.001465 |
| osc | tet12_note | sinusoid_module1 | 13 | 33.86 | 1 | 0.0002441 | 0.001465 |
| osc | linear_drift | sinusoid_drift | 13 | 18.68 | 1 | 0.0002441 | 0.001465 |
| osc | shruti22_note | sinusoid_drift | 13 | 31.17 | 1 | 0.0002441 | 0.001465 |
| osc | sinusoid_module1 | sinusoid_drift | 13 | 2.519 | 1 | 0.0002441 | 0.001465 |
| osc | steady_free | sinusoid_drift | 13 | 21.56 | 1 | 0.0002441 | 0.001465 |
| osc | tet12_framesnap | sinusoid_drift | 13 | -7.659 | 0.2812 | 0.003418 | 0.003418 |
| osc | tet12_note | sinusoid_drift | 13 | 34.83 | 1 | 0.0002441 | 0.001465 |