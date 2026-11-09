import numpy as np
from ornfid.models import fit_glide, fit_osc, snap_12tet, snap_shruti
from ornfid import detect


def test_cosine_exact_on_cosine_glide():
    u = np.linspace(0, 1, 100)
    y = 100 + 300 * (1 - np.cos(np.pi * u)) / 2
    p = fit_glide(y)
    assert np.sqrt(np.mean((y - p["cosine_module1"]) ** 2)) < 1e-6
    assert np.sqrt(np.mean((y - p["linear"]) ** 2)) > 1.0


def test_sinusoid_recovered():
    t = np.arange(200) * 0.01
    y = 50 + 40 * np.sin(2 * np.pi * 3.0 * t + 0.4)
    assert np.sqrt(np.mean((y - fit_osc(y)["sinusoid_module1"]) ** 2)) < 0.5


def test_snapping():
    assert snap_12tet(149.0) == 100.0
    assert abs(snap_shruti(498.0)[0] - 498.04) < 0.1


def test_detectors_find_planted_ornaments():
    t = np.arange(600) * 0.01
    glide = np.concatenate([np.zeros(100), 400 * (1 - np.cos(np.pi * np.linspace(0, 1, 100))) / 2, np.full(100, 400.0)])
    assert len(detect.detect_glides(glide)) == 1
    osc = 50 * np.sin(2 * np.pi * 3 * t)
    assert len(detect.detect_oscillations(osc)) >= 1


def test_plateau_ramp_beats_linear_on_plateau_glide():
    from ornfid.models import fit_glide
    u = np.linspace(0, 1, 120)
    phi = np.clip((u - 0.25) / 0.5, 0, 1)
    y = 100 + 300 * (1 - np.cos(np.pi * phi)) / 2
    p = fit_glide(y)
    rm = lambda m: np.sqrt(np.mean((y - p[m]) ** 2))  # noqa: E731
    assert rm("plateau_cosine") < 1.0 and rm("plateau_cosine") < rm("linear")


def test_param_extractors_recover_truth():
    from ornfid.models import glide_params, osc_params
    u = np.linspace(0, 1, 100)
    y = 100 + 300 * np.clip((u - 0.25) / 0.5, 0, 1)
    g = glide_params(y)
    assert abs(g["start"] - 100) < 1 and abs(g["end"] - 400) < 1 and abs(g["ramp_frac"] - 0.5) < 0.06
    t = np.arange(200) * 0.01
    o = osc_params(50 + 30 * t + 40 * np.sin(2 * np.pi * 3 * t + 0.3))
    assert abs(o["freq"] - 3.0) < 0.05 and abs(o["amp"] - 40) < 1 and abs(o["drift"] - 60) < 2


def test_raga_label_normalisation():
    from ornfid.io_saraga import _norm_label
    assert _norm_label("Raag Basanti Kedar") == "basanti kedar"
    assert _norm_label("Raga  Ramgauri & Gauri") == "ramgauri gauri"


def test_interior_preset_rejects_band_edge_wander_but_keeps_andolan_like_oscillation():
    t = np.arange(1200) * 0.01
    wander = 50 * np.sin(2 * np.pi * 0.6 * t)          # slow wander below the 1 Hz band edge
    osc = 50 * np.sin(2 * np.pi * 2.5 * t)
    assert len(detect.detect_oscillations(wander, detect.OSC_PRESETS["strict-osc"])) > 0   # the v0.4 artifact
    assert len(detect.detect_oscillations(wander, detect.OSC_PRESETS["interior-osc"])) == 0
    assert len(detect.detect_oscillations(osc, detect.OSC_PRESETS["interior-osc"])) > 0


def test_slow_preset_accepts_slow_oscillation_with_two_cycles_per_window():
    t = np.arange(1200) * 0.01
    assert len(detect.detect_oscillations(50 * np.sin(2 * np.pi * 0.7 * t), detect.OSC_PRESETS["slow-osc"])) > 0


def test_interior_wide_keeps_fast_oscillation_and_rejects_slow_wander():
    t = np.arange(1200) * 0.01
    P = detect.OSC_PRESETS["interior-wide"]
    assert len(detect.detect_oscillations(50 * np.sin(2 * np.pi * 5.2 * t), P)) > 0     # 4-6 Hz kept (strict presets dropped it)
    assert len(detect.detect_oscillations(50 * np.sin(2 * np.pi * 0.6 * t), P)) == 0


def test_andolan_preset_keeps_slow_and_rejects_fast_and_wander():
    t = np.arange(1200) * 0.01
    P = detect.OSC_PRESETS["andolan"]
    assert len(detect.detect_oscillations(50 * np.sin(2 * np.pi * 2.0 * t), P)) > 0
    assert len(detect.detect_oscillations(50 * np.sin(2 * np.pi * 5.2 * t), P)) == 0
    assert len(detect.detect_oscillations(50 * np.sin(2 * np.pi * 0.6 * t), P)) == 0


def test_audit_page_offers_four_way_labels_for_oscillations_and_yes_no_for_glides():
    from ornfid.audit import choices_html
    osc = choices_html("osc", 7)
    for v in ("andolan", "kampit", "gamak", "other", "unsure"):
        assert f'value="{v}"' in osc
    gl = choices_html("glide", 8)
    assert 'value="yes"' in gl and 'value="no"' in gl and 'value="andolan"' not in gl
