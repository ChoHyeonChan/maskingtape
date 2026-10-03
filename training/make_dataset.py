# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이름 판정 모델 학습 데이터와 보고용(held-out) 평가 세트를 만든다 (#458).

동작 원리:
1. bench 생성기의 문장 템플릿을 **학습용과 보고용으로 가른다**(#456 원칙 — 번호가 4로 나눠 3이
   남는 템플릿은 보고용). 학습 데이터는 학습용 템플릿으로만, 평가 세트는 보고용 템플릿으로만
   만들어 "본 문장"으로 점수가 부풀지 않게 한다. 공격 문장(#549)도 종류마다 앞 2개는 학습,
   마지막 1개는 평가에만 쓴다.
2. 학습 예제는 core의 LLMNameDetector가 보내는 것과 **똑같은 형식**이다 — 같은 시스템 프롬프트,
   사용자 메시지 = 문서 원문, 정답 = `{"names": [...]}`(원문에 적힌 표기 그대로). 그래서 학습한
   모델을 Ollama에 올리면 core는 모델 이름만 바꾸면 된다.
3. 구성: 이름 있는 문서(한 문장·여러 문장) + 이름 없는 문서(빈 목록) + 혼동어 문장(직함+조사·지명·
   회사명·일반명사 — 규칙판이 틀리는 것들) + 단서 없는 이름(`어제 김하늘과 갔다`) + 공격 문장을 붙인
   문서(정답은 그대로 → 지시문을 무시하도록 학습).

값은 전부 합성이다. 같은 시드면 바이트 단위로 같은 파일이 나온다.

사용법 (저장소 루트, 프로젝트 venv):
    python -m training.make_dataset --out-dir training/data [--seed 458] [--train-size 12000]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

from maskingtape.detectors.personal.name_llm import _SYSTEM_PROMPT

from bench.generator.attacks import ATTACK_SENTENCES, _attach
from bench.generator.documents import (
    Document,
    generate_document,
    generate_negative_document,
    negative_templates,
    templates,
)

HELDOUT_EVERY = 4  # 번호 % 4 == 3 인 템플릿이 보고용

# 학습 전용 추가 템플릿 — 생성기에 없는 모양. 규칙판이 원리적으로 못 하는 "단서 없는 이름"(#458 본문 1번).
_TRAIN_NOCUE_TEMPLATES = [
    "어제 {name}과 같이 점심을 먹었다.",
    "{name}이 먼저 도착해서 자리를 잡아 두었다.",
    "회의에는 {name}, {name} 두 명이 참석했다.",
    "{name}한테 자료 보내 달라고 했어요.",
    "이번 건은 {name}가 맡기로 했습니다.",
    "{name}랑 통화했는데 내일 온대요.",
    "발표는 {name}이 하고 질의응답은 {name}이 받는다.",
    "{name} 쪽에서 아직 답이 없습니다.",
]
# 보고용 전용 — 학습에 없는 모양으로 "단서 없는 이름"을 잰다.
_HELDOUT_NOCUE_TEMPLATES = [
    "오늘 {name}은 휴가라서 {name}이 대신 처리합니다.",
    "{name}에게 전달 부탁드립니다.",
    "지난주에 {name}하고 같이 갔던 곳이에요.",
    "{name}도 참석한다고 들었습니다.",
]

# 혼동어 문장 — 이름이 하나도 없다(정답은 빈 목록). 규칙판이 틀리는 모양을 모았다:
# 직함+조사("차장은"), 성씨로 시작하는 업무어("정산", "구매"), 지명·회사명·일반명사("이상", "조정", "문서").
_CONFUSER_SENTENCES = [
    "차장은 이번 분기 실적을 보고했다.",
    "원장이 진료 시간을 조정했습니다.",
    "주임이 서류를 정리해 두었습니다.",
    "정산 담당 부서에서 확인 중입니다.",
    "구매 요청서는 금요일까지 제출하세요.",
    "홍보 자료는 다음 주에 배포됩니다.",
    "이상 없음으로 보고합니다.",
    "일정 조정이 필요하면 알려 주세요.",
    "문서 양식은 공용 폴더에 있습니다.",
    "강남구청에서 안내문이 왔습니다.",
    "김포공항에서 출발하는 항공편입니다.",
    "한강공원에서 행사가 열립니다.",
    "삼성전자와 계약을 체결했습니다.",
    "현대자동차 서비스센터에 입고했습니다.",
    "마스킹테이프 주식회사가 공급자입니다.",
    "대표 이사가 참석했습니다.",
    "이사회에서 안건이 통과되었습니다.",
    "박수로 환영해 주세요.",
    "최고 등급으로 평가되었습니다.",
    "조기 마감될 수 있습니다.",
    "신규 가입자는 안내 문자를 받습니다.",
    "장비 점검은 매주 월요일입니다.",
    "오전 반차 사용 가능합니다.",
    "안전 교육은 분기마다 진행됩니다.",
    "노무 상담은 인사팀으로 문의하세요.",
    "차량이 배정되었습니다.",
    "허가가 나면 바로 착수합니다.",
    "성과가 좋아서 포상이 있을 예정입니다.",
    "전주에서 열리는 행사입니다.",
    "서울역에서 만나기로 했습니다.",
    "부산지점 매출이 늘었습니다.",
    "고객센터 운영 시간은 9시부터 18시까지입니다.",
]


@dataclass(frozen=True)
class Split:
    name_templates: list[str]
    other_templates: list[str]  # 이름 자리표시자가 없는 긍정 템플릿(다른 개인정보만 있음)
    negative_templates: list[str]
    nocue_templates: list[str]
    attack_sentences: dict[str, tuple[str, ...]]


def split_templates(heldout: bool) -> Split:
    pick = (lambda i: i % HELDOUT_EVERY == HELDOUT_EVERY - 1) if heldout else (lambda i: i % HELDOUT_EVERY != HELDOUT_EVERY - 1)
    all_templates = templates()
    name_t = [t for i, t in enumerate(all_templates) if "{name}" in t and pick(i)]
    other_t = [t for i, t in enumerate(all_templates) if "{name}" not in t and pick(i)]
    neg_t = [t for i, t in enumerate(negative_templates()) if pick(i)]
    attacks = {
        tag: (sentences[-1:] if heldout else sentences[:-1]) for tag, sentences in ATTACK_SENTENCES.items()
    }
    return Split(
        name_templates=name_t,
        other_templates=other_t,
        negative_templates=neg_t,
        nocue_templates=_HELDOUT_NOCUE_TEMPLATES if heldout else _TRAIN_NOCUE_TEMPLATES,
        attack_sentences={k: tuple(v) for k, v in attacks.items()},
    )


def _join(docs: list[Document]) -> Document:
    """문장 여러 개를 공백으로 이어 한 문서로 — 라벨 위치를 앞 문장 길이만큼 민다."""
    text_parts: list[str] = []
    labels = []
    cursor = 0
    for i, d in enumerate(docs):
        if i > 0:
            text_parts.append(" ")
            cursor += 1
        text_parts.append(d.text)
        labels.extend(type(lb)(kind=lb.kind, start=lb.start + cursor, end=lb.end + cursor) for lb in d.labels)
        cursor += len(d.text)
    return Document(text="".join(text_parts), labels=labels, difficulty=docs[0].difficulty)


def _render_nocue(template: str, rng: random.Random) -> Document:
    # 생성기의 템플릿 렌더러를 그대로 쓴다 — {name}만 있는 템플릿이라 difficulty는 이름 표기에만 영향.
    return generate_document(rng, template=template)


def _sentence(split: Split, rng: random.Random) -> Document:
    """문장 하나 — 이름 있는 템플릿 60%, 다른 개인정보만 20%, 단서 없는 이름 10%, 부정 10%."""
    r = rng.random()
    if r < 0.6:
        return generate_document(rng, template=rng.choice(split.name_templates))
    if r < 0.8:
        return generate_document(rng, template=rng.choice(split.other_templates))
    if r < 0.9:
        return _render_nocue(rng.choice(split.nocue_templates), rng)
    return generate_negative_document(rng, template=rng.choice(split.negative_templates))


def _confuser(rng: random.Random) -> Document:
    return Document(text=rng.choice(_CONFUSER_SENTENCES), labels=[], difficulty="negative")


def generate_documents(split: Split, seed: int, count: int) -> list[dict]:
    """bench 데이터셋 포맷(text/labels/difficulty) + attack_tag(없으면 "none")."""
    rng = random.Random(f"{seed}:{count}")
    rows: list[dict] = []
    while len(rows) < count:
        r = rng.random()
        if r < 0.35:
            doc = _sentence(split, rng)
        elif r < 0.75:
            n = rng.choice([2, 2, 3, 4])
            parts = [_sentence(split, rng) for _ in range(n)]
            if rng.random() < 0.3:
                parts.insert(rng.randrange(len(parts) + 1), _confuser(rng))
            doc = _join(parts)
        elif r < 0.85:
            doc = _confuser(rng)
        else:
            doc = _join([_confuser(rng), _sentence(split, rng)] if rng.random() < 0.5 else [_sentence(split, rng), _confuser(rng)])
        labels = [{"kind": lb.kind, "start": lb.start, "end": lb.end} for lb in doc.labels]
        text = doc.text
        attack_tag = "none"
        if rng.random() < 0.2:
            attack_tag = rng.choice(list(split.attack_sentences))
            text, labels = _attach(text, labels, rng.choice(split.attack_sentences[attack_tag]), rng.choice(["prefix", "suffix"]))
        rows.append({"text": text, "labels": labels, "difficulty": doc.difficulty, "attack_tag": attack_tag})
    return rows


def names_of(row: dict) -> list[str]:
    seen: dict[str, None] = {}
    for lb in row["labels"]:
        if lb["kind"] == "name":
            seen.setdefault(row["text"][lb["start"] : lb["end"]], None)
    return list(seen)


def to_sft(row: dict) -> dict:
    """core가 Ollama에 보내는 것과 같은 대화 — system은 core 상수, user는 원문, assistant는 JSON."""
    return {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": row["text"]},
            {"role": "assistant", "content": json.dumps({"names": names_of(row)}, ensure_ascii=False)},
        ]
    }


def heldout_attack_pairs(split: Split, seed: int, per_tag: int) -> list[dict]:
    """evaluate_attacks.py가 읽는 쌍 형식(pair_id로 묶인 깨끗한 판 + 공격 판) — 보고용 템플릿·보고용 공격 문장만."""
    rows: list[dict] = []
    pair_id = 0
    for tag, sentences in split.attack_sentences.items():
        rng = random.Random(f"{seed}:attack:{tag}")
        for _ in range(per_tag):
            doc = generate_document(rng, template=rng.choice(split.name_templates))
            labels = [{"kind": lb.kind, "start": lb.start, "end": lb.end} for lb in doc.labels]
            position = rng.choice(["prefix", "suffix"])
            attacked_text, attacked_labels = _attach(doc.text, labels, rng.choice(sentences), position)
            base = {"difficulty": "attack", "attack_position": position, "pair_id": pair_id}
            rows.append({"text": doc.text, "labels": labels, "attack_tag": "none", **base})
            rows.append({"text": attacked_text, "labels": attacked_labels, "attack_tag": tag, **base})
            pair_id += 1
    return rows


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="이름 판정 모델 학습 데이터·보고용 평가 세트 생성 (#458)")
    parser.add_argument("--out-dir", type=Path, default=Path("training/data"))
    parser.add_argument("--seed", type=int, default=458)
    parser.add_argument("--train-size", type=int, default=12000)
    parser.add_argument("--heldout-size", type=int, default=600)
    parser.add_argument("--heldout-attack-per-tag", type=int, default=20)
    args = parser.parse_args()

    train_split = split_templates(heldout=False)
    heldout_split = split_templates(heldout=True)
    train_rows = generate_documents(train_split, args.seed, args.train_size)
    write_jsonl([to_sft(r) for r in train_rows], args.out_dir / "train.jsonl")
    heldout = generate_documents(heldout_split, args.seed + 1, args.heldout_size)
    write_jsonl([{k: v for k, v in r.items() if k != "attack_tag"} for r in heldout if r["attack_tag"] == "none"],
                args.out_dir / "heldout_v1.jsonl")
    write_jsonl(heldout_attack_pairs(heldout_split, args.seed, args.heldout_attack_per_tag),
                args.out_dir / "heldout_attacks_v1.jsonl")

    with_names = sum(1 for r in train_rows if names_of(r))
    attacked = sum(1 for r in train_rows if r["attack_tag"] != "none")
    print(
        f"학습 {len(train_rows)}건 (이름 있음 {with_names}, 없음 {len(train_rows) - with_names}, 공격 문장 {attacked}) · "
        f"템플릿 학습용 {len(train_split.name_templates)}/보고용 {len(heldout_split.name_templates)}(이름) · "
        f"보고용 평가 {sum(1 for r in heldout if r['attack_tag'] == 'none')}건 + 공격 쌍 {5 * args.heldout_attack_per_tag} · "
        f"→ {args.out_dir}"
    )


if __name__ == "__main__":
    main()
