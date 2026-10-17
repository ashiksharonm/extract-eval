"""Gradio demo: score prediction JSONL against gold JSONL, or gate a candidate vs a baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gradio as gr
import yaml

from extract_eval import Config, evaluate, run_gate
from extract_eval.metrics import parse_jsonl
from extract_eval.report import render_markdown

HERE = Path(__file__).parent
EX = HERE / "examples" if (HERE / "examples").exists() else HERE.parent / "examples"
MAX_BYTES = 5_000_000
N_BOOT = 500


def _read(f: Any) -> str:
    path = Path(getattr(f, "name", f))
    if path.stat().st_size > MAX_BYTES:
        raise gr.Error(f"{path.name} is larger than {MAX_BYTES // 1_000_000} MB")
    return path.read_text(encoding="utf-8")


def _config(text: str) -> Config:
    try:
        return Config.from_dict(yaml.safe_load(text) or {})
    except Exception as exc:  # surface config problems to the user, not a stack trace
        raise gr.Error(f"Invalid config: {exc}") from exc


def _jsonl(f: Any, label: str) -> dict[str, dict[str, Any]]:
    if f is None:
        raise gr.Error(f"Upload the {label} JSONL file")
    try:
        return parse_jsonl(_read(f))
    except (ValueError, KeyError, AttributeError) as exc:
        raise gr.Error(f"{label}: not valid JSONL records ({exc})") from exc


def score(gold_f: Any, pred_f: Any, cfg_text: str) -> str:
    report = evaluate(_jsonl(gold_f, "gold"), _jsonl(pred_f, "prediction"),
                      _config(cfg_text), N_BOOT)
    return render_markdown(report)


def gate(gold_f: Any, base_f: Any, cand_f: Any, cfg_text: str, min_drop: float) -> str:
    from extract_eval.gate import render_gate_markdown

    res = run_gate(_jsonl(gold_f, "gold"), _jsonl(base_f, "baseline"),
                   _jsonl(cand_f, "candidate"), _config(cfg_text), N_BOOT, min_drop=min_drop)
    return render_gate_markdown(res)


def build() -> gr.Blocks:
    default_cfg = (EX / "receipts.yaml").read_text()
    with gr.Blocks(title="extract-eval") as demo:
        gr.Markdown(
            "# extract-eval\nScore structured-extraction output (Hungarian line-item matching, "
            "bootstrap CIs) or gate a candidate run against a baseline. Records are JSONL: "
            '`{"id": "r1", "data": {...}}`. Files are processed in memory and not stored.')
        cfg = gr.Code(value=default_cfg, language="yaml", label="Config (YAML)")
        with gr.Tab("Score"):
            g1, p1 = gr.File(label="gold.jsonl"), gr.File(label="predictions.jsonl")
            out1 = gr.Markdown()
            gr.Button("Score", variant="primary").click(score, [g1, p1, cfg], out1)
            gr.Examples([[str(EX / "gold.jsonl"), str(EX / "pred.jsonl")]], [g1, p1],
                        label="Bundled example")
        with gr.Tab("Regression gate"):
            g2, b2, c2 = (gr.File(label="gold.jsonl"), gr.File(label="baseline.jsonl"),
                          gr.File(label="candidate.jsonl"))
            md = gr.Slider(0, 0.2, value=0.0, step=0.005, label="Ignore drops smaller than")
            out2 = gr.Markdown()
            gr.Button("Run gate", variant="primary").click(gate, [g2, b2, c2, cfg, md], out2)
    return demo


if __name__ == "__main__":
    build().launch(server_name="0.0.0.0", server_port=7860)
