import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("gradio")
EX = Path(__file__).parent.parent / "examples"
SPEC = importlib.util.spec_from_file_location(
    "space_app", Path(__file__).parent.parent / "space" / "app.py")


@pytest.fixture(scope="module")
def app():
    mod = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(mod)
    return mod


def test_score_example(app):
    cfg = (EX / "receipts.yaml").read_text()
    md = app.score(str(EX / "gold.jsonl"), str(EX / "pred.jsonl"), cfg)
    assert md.startswith("# extract-eval report")


def test_gate_example_passes_when_identical(app):
    g = str(EX / "gold.jsonl")
    md = app.gate(g, g, g, (EX / "receipts.yaml").read_text(), 0.0)
    assert "PASSED" in md


def test_missing_upload_is_user_error(app):
    with pytest.raises(Exception, match="gold"):
        app.score(None, None, "default: text")


def test_blocks_builds(app):
    assert app.build() is not None
