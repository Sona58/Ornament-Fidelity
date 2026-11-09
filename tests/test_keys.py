from pathlib import Path

import numpy as np
import pytest

from ornfid import io_saraga as io


def _make(root: Path, release: str, stem: str):
    d = root / release / stem
    d.mkdir(parents=True)
    np.savetxt(d / f"{stem}.pitch.txt", np.column_stack([np.arange(0, 5, 0.01), np.full(500, 150.0)]))
    (d / f"{stem}.ctonic").write_text("146.8\n")


@pytest.fixture()
def root(tmp_path):
    for rel in ("Release A by X", "Release B by Y"):
        _make(tmp_path, rel, "Raag Yaman")          # same stem in two releases
    _make(tmp_path, "Release A by X", "Raag Bhairav")
    return tmp_path


def test_keys_are_unique_and_relative(root):
    recs = io.find_recordings(root)
    keys = [r.key for r in recs]
    assert len(set(keys)) == len(keys) == 3
    assert "Release A by X/Raag Yaman/Raag Yaman" in keys


def test_windows_style_full_path_matches_only_one(root):
    recs = io.find_recordings(root)
    m, un, amb = io.resolve_keys(recs, ["Release B by Y\\Raag Yaman\\Raag Yaman"], root)
    assert len(m) == 1 and not un and not amb
    assert next(r for r in recs if r.rec_id in m).rel_folder.startswith("Release B")


def test_extension_case_quotes_and_absolute_path(root):
    recs = io.find_recordings(root)
    entries = ['"release a by x/raag bhairav/Raag Bhairav.pitch.txt"',
               str(root / "Release A by X" / "Raag Yaman" / "Raag Yaman.ctonic")]
    m, un, amb = io.resolve_keys(recs, entries, root)
    assert len(m) == 2 and not un and not amb


def test_bare_stem_ambiguous_and_unique(root):
    recs = io.find_recordings(root)
    _, _, amb = io.resolve_keys(recs, ["Raag Yaman"], root)
    assert amb and len(amb[0][1]) == 2
    m, un, amb = io.resolve_keys(recs, ["Raag Bhairav"], root)
    assert len(m) == 1 and not un and not amb


def test_unmatched_stops_unless_ignored(root, tmp_path):
    recs = io.find_recordings(root)
    lst = tmp_path / "ex.txt"
    lst.write_text("# comment\nRelease A by X\\Raag Yamann\\Raag Yamann\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        io.apply_lists(recs, root, exclude_path=lst, log=lambda *_: None)
    kept = io.apply_lists(recs, root, exclude_path=lst, ignore_unmatched=True, log=lambda *_: None)
    assert len(kept) == 3


def test_exclude_and_include(root, tmp_path):
    recs = io.find_recordings(root)
    ex = tmp_path / "ex.txt"
    ex.write_text("Release A by X\\Raag Yaman\\Raag Yaman\n")
    kept = io.apply_lists(recs, root, exclude_path=ex, log=lambda *_: None)
    assert len(kept) == 2 and all(r.key != "Release A by X/Raag Yaman/Raag Yaman" for r in kept)
    inc = tmp_path / "in.txt"
    inc.write_text("Release B by Y\\Raag Yaman\\Raag Yaman\n")
    assert [r.key for r in io.apply_lists(recs, root, include_path=inc, log=lambda *_: None)] == \
        ["Release B by Y/Raag Yaman/Raag Yaman"]
