# Reconstruction results (RMSE in cents, lower = better)

Recordings used: 98; segments: 4675 (4653 glide-like, 22 oscillation-like).

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
| osc | tet12_note | 22 | 54.01 | 46.33 | 66.97 | 44.63 | 68.53 | 53.32 |
| osc | shruti22_note | 22 | 54.30 | 45.38 | 62.08 | 40.94 | 65.03 | 51.49 |
| osc | tet12_framesnap | 22 | 20.00 | 17.73 | 21.94 | 17.48 | 22.23 | 19.94 |
| osc | steady_free | 22 | 43.72 | 39.60 | 52.19 | 39.12 | 61.23 | 45.64 |
| osc | linear_drift | 22 | 42.83 | 36.74 | 51.33 | 33.48 | 59.00 | 43.14 |
| osc | sinusoid_module1 | 22 | 33.73 | 29.09 | 37.69 | 27.05 | 40.33 | 33.88 |
| osc | sinusoid_drift | 22 | 31.63 | 25.68 | 35.02 | 25.57 | 36.14 | 31.34 |


## Complexity-penalised comparison (share of segments where each parametric model has the lowest AICc)

| ornament | model | share_best_aicc |
|---|---|---|
| glide | linear | 0.501 |
| glide | cosine_module1 | 0.111 |
| glide | plateau_ramp | 0.300 |
| glide | plateau_cosine | 0.088 |
| osc | steady_free | 0.000 |
| osc | linear_drift | 0.000 |
| osc | sinusoid_module1 | 0.409 |
| osc | sinusoid_drift | 0.591 |


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
| osc | linear_drift | sinusoid_module1 | 13 | 9.958 | 0.9091 | 0.002441 | 0.004883 |
| osc | shruti22_note | sinusoid_module1 | 13 | 18.17 | 1 | 0.0002441 | 0.001465 |
| osc | sinusoid_drift | sinusoid_module1 | 13 | -1.523 | 0 | 0.0002441 | 0.001465 |
| osc | steady_free | sinusoid_module1 | 13 | 10.37 | 1 | 0.0002441 | 0.001465 |
| osc | tet12_framesnap | sinusoid_module1 | 13 | -11.97 | 0.1364 | 0.002441 | 0.004883 |
| osc | tet12_note | sinusoid_module1 | 13 | 18.17 | 1 | 0.0002441 | 0.001465 |
| osc | linear_drift | sinusoid_drift | 13 | 10.37 | 1 | 0.0002441 | 0.001465 |
| osc | shruti22_note | sinusoid_drift | 13 | 20.62 | 1 | 0.0002441 | 0.001465 |
| osc | sinusoid_module1 | sinusoid_drift | 13 | 1.523 | 1 | 0.0002441 | 0.001465 |
| osc | steady_free | sinusoid_drift | 13 | 15.17 | 1 | 0.0002441 | 0.001465 |
| osc | tet12_framesnap | sinusoid_drift | 13 | -9.824 | 0.1364 | 0.006104 | 0.006104 |
| osc | tet12_note | sinusoid_drift | 13 | 20.12 | 1 | 0.0002441 | 0.001465 |