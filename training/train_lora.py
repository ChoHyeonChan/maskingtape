# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""Qwen2.5-Instruct에 LoRA로 이름 추출을 가르친다 (#458).

동작 원리:
1. make_dataset.py가 만든 대화(system/user/assistant)를 모델의 채팅 템플릿으로 토큰화하고,
   **정답(assistant) 토큰에만 손실**을 건다 — 프롬프트·원문을 외우는 게 아니라 "이 문서에서 이름이
   무엇인가"만 배우게 한다.
2. 가중치 전체가 아니라 LoRA 어댑터(어텐션·MLP 선형층에 붙는 저랭크 행렬)만 학습한다. 1.5B는
   bf16 그대로 올려도 RTX 3080 10GB에 들어간다.
3. 결과는 어댑터만 저장한다. export_ollama.py가 기반 모델과 합쳐 GGUF로 만든다.

학습 라이브러리(torch·transformers·peft)는 개발 도구라 제품에 들어가지 않는다 — 전부 BSD/Apache-2.0.

사용법 (학습 venv — training/README.md):
    python training/train_lora.py --data training/data/train.jsonl --out D:/dev/train/runs/name-1.5b-v1
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

DEFAULT_BASE = "Qwen/Qwen2.5-1.5B-Instruct"  # Apache-2.0 (3B·72B는 비상업 라이선스라 쓰지 않는다)
IGNORE = -100


class ChatDataset(Dataset):
    """대화 한 건 → input_ids/labels. 프롬프트 부분의 label은 IGNORE."""

    def __init__(self, rows: list[dict], tokenizer, max_len: int):
        self.items = []
        skipped = 0
        for row in rows:
            messages = row["messages"]
            # 문자열로 받아 직접 토큰화한다 — transformers 판에 따라 tokenize=True의 반환형이 달라서(list / BatchEncoding).
            prompt_text = tokenizer.apply_chat_template(messages[:-1], add_generation_prompt=True, tokenize=False)
            prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
            # Qwen 템플릿은 assistant 차례를 <|im_end|>\n 으로 닫는다 — 모델이 멈추는 법도 같이 배운다.
            answer_ids = tokenizer(messages[-1]["content"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
            ids = prompt_ids + answer_ids
            if len(ids) > max_len:
                skipped += 1
                continue
            labels = [IGNORE] * len(prompt_ids) + answer_ids
            self.items.append((ids, labels))
        if skipped:
            print(f"[안내] max_len={max_len}을 넘는 {skipped}건은 뺐습니다")

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        ids, labels = self.items[i]
        return {"input_ids": ids, "labels": labels}


def make_collator(pad_id: int):
    def collate(batch):
        width = max(len(b["input_ids"]) for b in batch)
        input_ids = torch.full((len(batch), width), pad_id, dtype=torch.long)
        labels = torch.full((len(batch), width), IGNORE, dtype=torch.long)
        attention = torch.zeros((len(batch), width), dtype=torch.long)
        for i, b in enumerate(batch):
            n = len(b["input_ids"])
            input_ids[i, :n] = torch.tensor(b["input_ids"])
            labels[i, :n] = torch.tensor(b["labels"])
            attention[i, :n] = 1
        return {"input_ids": input_ids, "labels": labels, "attention_mask": attention}

    return collate


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="이름 추출 LoRA 학습 (#458)")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="어댑터 저장 폴더")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--grad-accum", type=int, default=2)
    parser.add_argument("--max-len", type=int, default=640)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--eval-frac", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=458)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU가 필요합니다")
    torch.manual_seed(args.seed)

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    rows = load_rows(args.data)
    random.Random(args.seed).shuffle(rows)
    n_eval = max(1, int(len(rows) * args.eval_frac))
    eval_ds = ChatDataset(rows[:n_eval], tokenizer, args.max_len)
    train_ds = ChatDataset(rows[n_eval:], tokenizer, args.max_len)
    print(f"학습 {len(train_ds)}건 / 검증 {len(eval_ds)}건 · 기반 {args.base}")

    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.bfloat16, device_map="cuda")
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = get_peft_model(
        model,
        LoraConfig(
            r=args.rank,
            lora_alpha=args.rank * 2,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            task_type="CAUSAL_LM",
        ),
    )
    model.print_trainable_parameters()

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(args.out / "checkpoints"),
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            per_device_train_batch_size=args.batch,
            per_device_eval_batch_size=args.batch,
            gradient_accumulation_steps=args.grad_accum,
            lr_scheduler_type="cosine",
            warmup_steps=50,  # transformers 5에는 warmup_ratio가 없다
            bf16=True,
            logging_steps=20,
            eval_strategy="steps",
            eval_steps=200,
            save_strategy="no",
            report_to=[],
            seed=args.seed,
            dataloader_pin_memory=False,
        ),
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=make_collator(tokenizer.pad_token_id),
    )
    trainer.train()
    metrics = trainer.evaluate()
    print("검증 손실:", round(metrics["eval_loss"], 4))

    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out / "adapter")
    tokenizer.save_pretrained(args.out / "adapter")
    (args.out / "train_info.json").write_text(
        json.dumps({"base": args.base, "args": vars(args) | {"data": str(args.data), "out": str(args.out)},
                    "train_rows": len(train_ds), "eval_loss": metrics["eval_loss"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("어댑터 저장:", args.out / "adapter")


if __name__ == "__main__":
    main()
