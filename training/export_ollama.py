# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""학습한 LoRA 어댑터를 기반 모델과 합쳐 Ollama 모델로 만든다 (#458).

동작 원리:
1. 기반 모델(bf16) 위에 어댑터를 올리고 merge_and_unload()로 하나의 가중치로 합쳐 safetensors로 저장한다
   (이 폴더가 허깅페이스에 공개할 가중치다 — 규정 제9조 ②항 2호 나목).
2. llama.cpp의 convert_hf_to_gguf.py(MIT)로 f16 GGUF를 만들고, llama-quantize(같은 저장소의 공식 빌드)로
   Q4_K_M으로 양자화한다 — Ollama 라이브러리의 `qwen2.5:1.5b`와 같은 양자화라 크기·속도 비교가 공정하다.
   (Ollama의 `create -q`는 safetensors에서만 되고 그 경로는 Qwen2를 아직 지원하지 않는다 — 직접 확인.)
3. Modelfile(FROM 양자화 GGUF, temperature 0, 라이선스)로 `ollama create` — core는 `--llm-model`에 이 이름만 주면 된다.

사용법 (학습 venv, Ollama 서버 실행 중):
    python training/export_ollama.py --run D:/dev/train/runs/name-1.5b-v1 --name maskingtape-name:1.5b
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_LLAMA_CPP = Path("D:/dev/llama.cpp")  # git clone (변환 스크립트)
DEFAULT_LLAMA_QUANTIZE = Path("D:/dev/llama.cpp-bin/llama-quantize.exe")  # 공식 릴리스 zip(bin-win-cpu-x64)

MODELFILE = """FROM {source}
# core의 LLMNameDetector가 요청마다 system·temperature를 보내지만, 직접 쓸 때도 같은 조건이 되게 둔다.
PARAMETER temperature 0
PARAMETER num_ctx 4096
LICENSE \"\"\"Apache-2.0 — The maskingtape Authors (2026).
Fine-tuned from {base} (Apache-2.0, Alibaba Cloud Qwen team) on synthetic Korean documents only.
https://github.com/ChoHyeonChan/maskingtape
\"\"\"
"""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def merge(run: Path) -> tuple[Path, str]:
    info = json.loads((run / "train_info.json").read_text(encoding="utf-8"))
    base = info["base"]
    merged = run / "merged"
    if merged.exists():
        shutil.rmtree(merged)
    tokenizer = AutoTokenizer.from_pretrained(run / "adapter")
    model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, run / "adapter").merge_and_unload()
    model.save_pretrained(merged, safe_serialization=True)
    tokenizer.save_pretrained(merged)
    print("합친 가중치:", merged)
    return merged, base


def to_gguf(merged: Path, llama_cpp: Path) -> Path:
    out = merged.parent / "model-f16.gguf"
    subprocess.run(
        [sys.executable, str(llama_cpp / "convert_hf_to_gguf.py"), str(merged), "--outtype", "f16", "--outfile", str(out)],
        check=True,
    )
    print("GGUF:", out, f"({out.stat().st_size / 1e9:.2f} GB)")
    return out


def quantize(gguf_f16: Path, llama_quantize: Path, quant: str) -> Path:
    out = gguf_f16.with_name(f"model-{quant.lower()}.gguf")
    subprocess.run([str(llama_quantize), str(gguf_f16), str(out), quant], check=True)
    print("양자화:", out, f"({out.stat().st_size / 1e6:.0f} MB)")
    return out


def register(gguf: Path, base: str, name: str) -> None:
    modelfile = gguf.parent / "Modelfile"
    modelfile.write_text(MODELFILE.format(source=gguf.name, base=base), encoding="utf-8")
    subprocess.run(["ollama", "create", name, "-f", str(modelfile)], check=True, cwd=gguf.parent)
    show = subprocess.run(["ollama", "show", name], check=True, capture_output=True, text=True, encoding="utf-8").stdout
    print(show)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="LoRA 어댑터 → 합친 가중치 → GGUF → Ollama 모델 (#458)")
    parser.add_argument("--run", type=Path, required=True, help="train_lora.py의 --out 폴더")
    parser.add_argument("--name", default="maskingtape-name:1.5b", help="Ollama 모델 이름")
    parser.add_argument("--quant", default="Q4_K_M", help="llama-quantize 형식")
    parser.add_argument("--llama-cpp", type=Path, default=DEFAULT_LLAMA_CPP)
    parser.add_argument("--llama-quantize", type=Path, default=DEFAULT_LLAMA_QUANTIZE)
    parser.add_argument("--skip-merge", action="store_true", help="이미 합친 가중치·f16 GGUF가 있으면 양자화·등록만")
    args = parser.parse_args()

    if args.skip_merge:
        merged = args.run / "merged"
        base = json.loads((args.run / "train_info.json").read_text(encoding="utf-8"))["base"]
        gguf_f16 = args.run / "model-f16.gguf"
    else:
        merged, base = merge(args.run)
        gguf_f16 = to_gguf(merged, args.llama_cpp)
    gguf = quantize(gguf_f16, args.llama_quantize, args.quant)
    register(gguf, base, args.name)
    print("양자화 GGUF sha256:", sha256_of(gguf), f"({gguf.stat().st_size:,} bytes)")
    print(f"core에서 쓰기: maskingtape --llm --llm-model {args.name}  (또는 DEFAULT_MODEL 변경)")


if __name__ == "__main__":
    main()
