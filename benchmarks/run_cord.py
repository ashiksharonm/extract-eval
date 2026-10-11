"""Run Donut (CORD-v2 fine-tuned) on the CORD-v2 test split and write gold/pred JSONL.

Produces two prediction files from ONE greedy decode per document:
  preds_full.jsonl   - full greedy decode (max_length=768)
  preds_trunc.jsonl  - the same decode cut to the first N tokens. Greedy decoding is
                       prefix-consistent, so this equals running with max_length=N.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import time
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

MODEL = "naver-clova-ix/donut-base-finetuned-cord-v2"
KEEP = {"menu", "sub_total", "total"}


def canon(parse: dict) -> dict:
    return {k: v for k, v in parse.items() if k in KEEP}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default="benchmarks/cord_v2")
    ap.add_argument("--trunc-tokens", type=int, default=96)
    ap.add_argument("--max-length", type=int, default=768)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = DonutProcessor.from_pretrained(MODEL)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL).to(device).eval()
    ds = load_dataset("naver-clova-ix/cord-v2", split="test")
    n = min(a.n, len(ds))
    prompt = proc.tokenizer("<s_cord-v2>", add_special_tokens=False, return_tensors="pt").input_ids

    def to_json(ids: list[int]) -> dict:
        seq = proc.tokenizer.decode(ids)
        seq = seq.replace(proc.tokenizer.eos_token, "").replace(proc.tokenizer.pad_token, "")
        seq = re.sub(r"<.*?>", "", seq, count=1).strip()
        try:
            return canon(proc.token2json(seq))
        except Exception:
            return {}

    t0 = time.time()
    with (out / "gold.jsonl").open("w") as fg, (out / "preds_full.jsonl").open("w") as ff, \
            (out / "preds_trunc.jsonl").open("w") as ft:
        for i in range(n):
            ex = ds[i]
            gold = canon(json.loads(ex["ground_truth"])["gt_parse"])
            pix = proc(ex["image"].convert("RGB"), return_tensors="pt").pixel_values.to(device)
            with torch.no_grad():
                gen = model.generate(
                    pix, decoder_input_ids=prompt.to(device), max_length=a.max_length,
                    pad_token_id=proc.tokenizer.pad_token_id,
                    eos_token_id=proc.tokenizer.eos_token_id, use_cache=True, num_beams=1,
                    bad_words_ids=[[proc.tokenizer.unk_token_id]],
                )
            ids = gen[0].tolist()
            did = f"cord_test_{i:03d}"
            fg.write(json.dumps({"id": did, "data": gold}, ensure_ascii=False) + "\n")
            ff.write(json.dumps({"id": did, "data": to_json(ids)}, ensure_ascii=False) + "\n")
            # ids[0] is the prompt token; keep it plus the first N generated tokens
            ft.write(json.dumps({"id": did, "data": to_json(ids[: a.trunc_tokens + 1])},
                                ensure_ascii=False) + "\n")
            for f in (fg, ff, ft):
                f.flush()
            print(f"{i + 1}/{n} {time.time() - t0:.0f}s", flush=True)
    meta = {
        "model": MODEL, "dataset": "naver-clova-ix/cord-v2 test", "n_docs": n,
        "device": device, "hardware": "Apple M5, 16 GB unified memory",
        "torch": torch.__version__, "python": platform.python_version(),
        "decoding": f"greedy, num_beams=1, max_length={a.max_length}",
        "weak_variant": f"same greedy decode truncated to first {a.trunc_tokens} generated tokens",
        "runtime_seconds": round(time.time() - t0, 1),
        "seconds_per_doc": round((time.time() - t0) / n, 2),
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=2))
    print(meta)


if __name__ == "__main__":
    main()
