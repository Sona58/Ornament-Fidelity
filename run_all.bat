@echo off
REM Usage: run_all.bat "D:\path\to\saraga_hindustani"
set ROOT=%~1
if "%ROOT%"=="" (echo Usage: run_all.bat "path\to\saraga_hindustani" & exit /b 1)
python scripts\01_run_reconstruction.py --saraga-root "%ROOT%" --out results || exit /b 1
python scripts\02_make_figures.py --results results --spectrograms
python scripts\03_render_audio_samples.py --results results
python scripts\05_sensitivity.py --saraga-root "%ROOT%" --out results_sens
REM Optional (needs Python>=3.10 + pennylane):  python scripts\04_verify_cv_equivalence.py
python scripts\06_audit_helper.py --results results
REM Optional downstream test:  python scripts\07_raga_classification.py --saraga-root "%ROOT%" --out results_raga
