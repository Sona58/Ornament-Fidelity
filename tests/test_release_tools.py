import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_wilson_interval_matches_paper_value():
    m = _load("scripts/08_audit_analysis.py", "audit08")
    p, lo, hi = m.wilson(41, 58)
    assert abs(p - 0.707) < 0.001 and abs(lo - 0.580) < 0.002 and abs(hi - 0.808) < 0.002
    p, lo, hi = m.wilson(35, 40)
    assert abs(lo - 0.739) < 0.002 and abs(hi - 0.945) < 0.002


def test_config_is_stripped_of_local_paths():
    t = _load("tools/prepare_paper_results.py", "prep")
    cfg = {"args": {"saraga_root": "D:\\someone\\data\\saraga", "out": "results_iw",
                    "exclude_list": "C:\\x\\exclude_recordings.txt", "audit_exclude": "['results_iw\\\\audit_sheet.csv']",
                    "seed": "0"}}
    out = t.clean_config(cfg)["args"]
    assert out["saraga_root"] == "<SARAGA_ROOT>"
    assert out["exclude_list"] == "exclude_recordings.txt"
    assert out["audit_exclude"] == "audit_sheet.csv"
    assert "someone" not in str(out)
