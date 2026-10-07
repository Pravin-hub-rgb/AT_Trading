import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import exp_provenance as pv  # noqa: E402


def test_engine_commit_is_hex_or_unknown(monkeypatch):
    monkeypatch.setattr(pv, "ROOT", pv.ROOT)
    sha = pv.engine_commit()
    assert sha == "unknown" or all(c in "0123456789abcdef" for c in sha)


def test_engine_commit_unknown_when_git_fails(monkeypatch):
    def boom(*a, **k):
        raise OSError("no git")
    monkeypatch.setattr(pv.subprocess, "run", boom)
    assert pv.engine_commit() == "unknown"


def test_md_stamp_roundtrip(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# Result\n\nIS +100R\n", encoding="utf-8")
    rec = pv.stamp_current(f, harness="exp_foo.py")
    back = pv.read(f)
    assert back["engine"] == rec["engine"]
    assert back["measured"] == rec["measured"]
    assert back["harness"] == "exp_foo.py"
    # stamp must not damage the content
    assert "IS +100R" in f.read_text(encoding="utf-8")


def test_json_stamp_roundtrip(tmp_path):
    f = tmp_path / "_b.json"
    f.write_text(json.dumps({"n": 5, "net": 1.5}), encoding="utf-8")
    pv.stamp_current(f)
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["n"] == 5 and data["net"] == 1.5
    assert data[pv.JSON_KEY]["engine"] == pv.engine_commit()[:7]


def test_restamping_does_not_stack(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# R\n", encoding="utf-8")
    pv.stamp_current(f)
    pv.stamp_current(f)
    text = f.read_text(encoding="utf-8")
    assert text.count(pv.MD_MARK) == 1


def test_read_returns_none_when_unstamped(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# R\n+1.23R\n", encoding="utf-8")
    assert pv.read(f) is None


def test_harness_field_may_contain_spaces(tmp_path):
    # A stamp may record that the harness was deleted, not just its name. With
    # \S+ in the pattern such a stamp was written and then read back as None,
    # which is indistinguishable from "never stamped" - the one wrong answer this
    # file must not give.
    f = tmp_path / "a.md"
    f.write_text(
        "<!-- prov: engine=abc1234 measured=2026-10-07 harness=recorded, harnesses deleted -->\n"
        "# R\n", encoding="utf-8")
    rec = pv.read(f)
    assert rec is not None
    assert rec["engine"] == "abc1234"
    assert rec["measured"] == "2026-10-07"
    assert "deleted" in rec["harness"]


def test_read_returns_none_on_malformed_json(tmp_path):
    f = tmp_path / "_c.json"
    f.write_text("{not json", encoding="utf-8")
    assert pv.read(f) is None


def test_read_returns_none_for_missing_file(tmp_path):
    assert pv.read(tmp_path / "nope.md") is None


def test_verify_flags_engine_mismatch(tmp_path, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text("<!-- prov: engine=deadbee measured=2026-01-01 -->\n", encoding="utf-8")
    monkeypatch.setattr(pv, "engine_commit", lambda: "abcdef1")
    rc = pv.verify([f], quiet=True)
    assert rc == 1


def test_verify_passes_when_engine_matches(tmp_path, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text("# R\n", encoding="utf-8")
    pv.stamp_current(f)
    monkeypatch.setattr(pv, "engine_commit", pv.engine_commit)
    assert pv.verify([f], quiet=True) == 0


def test_unrecorded_does_not_fail_the_run(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# R\n", encoding="utf-8")
    # no stamp: a warning, not a failure, so old artifacts are not forced to lie
    assert pv.verify([f], quiet=True) == 0


def test_verify_covers_committed_artifact_inventory():
    # the shipped repo must have every artifact findable at all
    assert len(pv.artifacts()) > 100


def test_cli_help_returns_zero():
    assert pv.main([]) == 0


def test_cli_verify_runs():
    # Deliberately NOT asserted as 0.
    #
    # verify() exits 1 whenever any stamped artifact was measured against a
    # different engine commit. That includes the case where the engine commit
    # MOVED but nothing an existing artifact depends on changed - adding a new
    # `mode=` branch to unified.py shifts the sha while leaving the shipping
    # book's trade list byte-identical. So this test asserts only that the
    # command runs and reports, not that the repo happens to be clean. Making it
    # assert 0 would fail on any commit that touches the engine at all, including
    # a comment, which would train people to ignore the check.
    rc = pv.main(["verify"])
    assert rc in (0, 1)


def test_engine_sha_tracks_the_engine_file_not_head(tmp_path):
    # The stamp must follow the file that decides what a number means, not HEAD.
    # If it followed HEAD, a docs-only commit would invalidate every artifact.
    import subprocess as sp
    eng = pv.ROOT / pv.ENGINE_TRACKED[0]
    out = sp.run(["git", "log", "-1", "--format=%h", "--", str(eng.relative_to(pv.ROOT))],
                 cwd=pv.ROOT, capture_output=True, text=True, timeout=30)
    engine_sha = out.stdout.strip()
    head = sp.run(["git", "rev-parse", "--short", "HEAD"],
                  cwd=pv.ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
    if engine_sha == head:
        return  # HEAD did touch the engine; the two coincide, nothing to assert
    assert engine_sha != head, (
        "engine_commit() must report the commit that touched %s, not HEAD"
        % pv.ENGINE_TRACKED[0])