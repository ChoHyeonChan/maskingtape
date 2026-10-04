# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이름 판정 모델 학습 데이터와 보고용(held-out) 평가 세트를 만든다 (#458).

v3부터 이름 뒤 조사를 받침에 맞게 고친다(fix_josa) — 생성기 템플릿의 고정 조사("{name}은")가 "서아은" 같은
틀린 문장을 만들어 경계 오류의 절반을 차지했다. 보고용 파일은 heldout_v2(교정본)로 쓴다.

동작 원리:
1. bench 생성기의 문장 템플릿을 **학습용과 보고용으로 가른다**(#456 원칙 — 번호가 4로 나눠 3이
   남는 템플릿은 보고용). 학습 데이터는 학습용 템플릿으로만, 평가 세트는 보고용 템플릿으로만
   만들어 "본 문장"으로 점수가 부풀지 않게 한다. 공격 문장(#549)도 종류마다 앞 2개는 학습,
   마지막 1개는 평가에만 쓴다. **예외: 혼동어 문장(_CONFUSER_SENTENCES 32개)은 학습과 보고용이
   공유한다** — 보고용 463건 중 172건이 포함하므로 보고용 오탐 수치는 낙관적일 수 있다(README 「평가 한계」).
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
    # v2 — 1차 보고용 오류(2음절 이름 + 조사 은/도를 이름에 붙임) 보강: 조사 종류를 넓힌다.
    "{name}은 오늘 재택이라 {name}이 대신 받습니다.",
    "{name}도 같이 가기로 했어요.",
    "{name}는 아직 출근 전입니다.",
    "{name}만 빠지고 다 왔습니다.",
    "{name}께 보고드렸습니다.",
    "{name}에게도 알려 주세요.",
    "{name}은 어제 퇴근 후 연락이 안 됐다.",
    "다음 발표는 {name}도 함께 준비한다.",
    "{name}은 회의실에, {name}도 곧 옵니다.",
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
# v2 — 1차 보고용 오류("자택"·"안내"·"신주소"를 이름으로) 보강: 문장 첫머리·번호 앞에 오는 생활어·업무어. 학습에만 쓴다.
_TRAIN_EXTRA_CONFUSERS = [
    "자택 번호와 직장 번호를 모두 적어 주세요.",
    "자택으로 우편을 보냈습니다.",
    "자택 전화는 저녁에만 받습니다.",
    "자택 근무로 전환되었습니다.",
    "직장 전화는 근무 시간에만 받습니다.",
    "직장 건강검진 일정이 나왔습니다.",
    "신주소로 변경 신청이 접수되었습니다.",
    "주소 변경 후 신주소가 반영되었습니다.",
    "본사 이전으로 신주소 안내드립니다.",
    "안내 문자가 발송되었습니다.",
    "안내 데스크는 1층에 있습니다.",
    "회신 기한은 금요일까지입니다.",
    "접수 번호를 확인해 주세요.",
    "재택 근무 신청서를 제출했습니다.",
    "휴대폰 번호가 바뀌면 알려 주세요.",
    "사무실 번호로 연락 주시면 됩니다.",
    "배송지 변경은 출고 전까지 가능합니다.",
    "수령인 정보가 비어 있습니다.",
    "담당자 배정이 아직 안 됐습니다.",
    "문의 사항은 게시판에 남겨 주세요.",
]


# v3 — 1차·2차 보고용 오류의 큰 몫(2음절 이름 + 조사 경계)이 생성기 문장의 **틀린 조사** 때문이었다:
# 템플릿이 `{name}은`처럼 조사를 고정해 "서아은"(받침 없는 이름 + 은)이 만들어졌고, 모델은 이를 3음절
# 이름으로 읽었다 — 한국어로는 "서아는"이 맞다. 렌더된 문서에서 이름 라벨 바로 뒤의 조사를 받침에 맞게
# 고친다(es-hangul의 josa와 같은 규칙, 우리가 쓴 코드). 받침 ㄹ 뒤는 "으로"가 아니라 "로"다.
_JOSA_PAIRS: tuple[tuple[str, str], ...] = (  # (받침 있을 때, 없을 때) — 긴 것부터 본다
    ("으로", "로"), ("이랑", "랑"), ("이나", "나"), ("이며", "며"), ("이고", "고"),
    ("이", "가"), ("은", "는"), ("을", "를"), ("과", "와"), ("아", "야"),
)
_JOSA_VARIANTS = sorted({v for pair in _JOSA_PAIRS for v in pair}, key=len, reverse=True)
_JOSA_BOUNDARY = " ,.!?)\n"


def _batchim(ch: str) -> int | None:
    """음절의 받침 번호(0이면 없음). 한글 음절이 아니면 None."""
    code = ord(ch) - 0xAC00
    return code % 28 if 0 <= code < 11172 else None


def correct_josa(word: str, josa: str) -> str:
    """word 뒤에 올 조사의 올바른 형태. josa는 _JOSA_PAIRS의 어느 한쪽."""
    for with_b, without_b in _JOSA_PAIRS:
        if josa in (with_b, without_b):
            b = _batchim(word[-1])
            if b is None:
                return josa
            if with_b == "으로":
                return "로" if b in (0, 8) else "으로"  # ㄹ 받침(8)은 "로"
            return with_b if b else without_b
    return josa


def fix_josa(text: str, labels: list[dict]) -> tuple[str, list[dict]]:
    """이름 라벨 바로 뒤의 조사를 받침에 맞게 고치고, 길이가 달라지면 뒤 라벨 위치를 민다."""
    labels = sorted((dict(lb) for lb in labels), key=lambda lb: lb["start"])
    out = text
    for i, lb in enumerate(labels):
        if lb["kind"] != "name":
            continue
        end = lb["end"]
        for josa in _JOSA_VARIANTS:
            after = end + len(josa)
            if out.startswith(josa, end) and (after == len(out) or out[after] in _JOSA_BOUNDARY):
                fixed = correct_josa(out[lb["start"]:end], josa)
                if fixed != josa:
                    out = out[:end] + fixed + out[after:]
                    delta = len(fixed) - len(josa)
                    for later in labels[i + 1:]:
                        later["start"] += delta
                        later["end"] += delta
                break
    return out, labels


# v3 — 직함 뒤 2음절 업무어("팀장 안내가", "구매 부장이")를 이름으로 보는 오탐 보강. 보고용 부정 템플릿에
# 나오는 단어(안내·구매·전입·홍보·정기·안전·노무·차량·허가·성과)는 **일부러 빼고** 다른 업무어로 만든다 —
# 단어를 외우는 게 아니라 "직함 + 업무어 + 조사" 모양을 배우는지가 보고용 세트에서 드러나게.
_TRAIN_TITLE_WORD_CONFUSERS = [
    "팀장 결재가 끝났습니다.", "과장 승인이 필요합니다.", "부장 보고가 늦어졌습니다.", "대리 출장이 잡혔습니다.",
    "팀장 교육이 다음 주에 있습니다.", "부장 검수가 끝나야 출고됩니다.", "과장 점검이 매주 있습니다.",
    "대표 결재가 나면 착수합니다.", "이사 승인을 받았습니다.", "실장 보고를 먼저 올리세요.",
    "팀장 회의가 3시로 바뀌었습니다.", "부장 면담은 금요일입니다.", "과장 평가가 반영되었습니다.",
    "영업 팀장이 방문했습니다.", "총무 과장이 안건을 올렸습니다.", "기획 부장이 발표했습니다.",
    "회계 담당자가 확인 중입니다.", "법무 검토가 끝났습니다.", "전산 점검으로 접속이 끊깁니다.",
    "시설 보수가 예정되어 있습니다.", "복지 안건은 다음 회의로 넘깁니다.", "채용 공고가 올라갔습니다.",
    "급여 명세서는 25일에 나옵니다.", "세무 신고 기한이 다가옵니다.", "연구 과제가 선정되었습니다.",
    "물류 창고가 이전합니다.", "품질 검사를 통과했습니다.", "생산 일정이 앞당겨졌습니다.",
    "조달 계약이 체결되었습니다.", "발주 수량을 확인해 주세요.", "입고 처리가 완료되었습니다.",
    "감사 결과가 공유되었습니다.", "연수 신청은 이번 주까지입니다.", "배송 지연이 발생했습니다.",
    "설비 교체가 끝났습니다.", "계약 갱신 통지가 나갈 예정입니다.",
]


@dataclass(frozen=True)
class Split:
    name_templates: list[str]
    other_templates: list[str]  # 이름 자리표시자가 없는 긍정 템플릿(다른 개인정보만 있음)
    negative_templates: list[str]
    nocue_templates: list[str]
    confusers: list[str]
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
        confusers=_CONFUSER_SENTENCES if heldout else _CONFUSER_SENTENCES + _TRAIN_EXTRA_CONFUSERS + _TRAIN_TITLE_WORD_CONFUSERS,
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


def _confuser(split: Split, rng: random.Random) -> Document:
    return Document(text=rng.choice(split.confusers), labels=[], difficulty="negative")


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
                parts.insert(rng.randrange(len(parts) + 1), _confuser(split, rng))
            doc = _join(parts)
        elif r < 0.85:
            doc = _confuser(split, rng)
        else:
            doc = _join([_confuser(split, rng), _sentence(split, rng)] if rng.random() < 0.5 else [_sentence(split, rng), _confuser(split, rng)])
        labels = [{"kind": lb.kind, "start": lb.start, "end": lb.end} for lb in doc.labels]
        text, labels = fix_josa(doc.text, labels)
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
            text, labels = fix_josa(doc.text, [{"kind": lb.kind, "start": lb.start, "end": lb.end} for lb in doc.labels])
            position = rng.choice(["prefix", "suffix"])
            attacked_text, attacked_labels = _attach(text, labels, rng.choice(sentences), position)
            base = {"difficulty": "attack", "attack_position": position, "pair_id": pair_id}
            rows.append({"text": text, "labels": labels, "attack_tag": "none", **base})
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
    # v2: 조사 교정 적용본. v1(교정 전)은 1차·2차 결과의 근거로 그대로 둔다.
    write_jsonl([{k: v for k, v in r.items() if k != "attack_tag"} for r in heldout if r["attack_tag"] == "none"],
                args.out_dir / "heldout_v2.jsonl")
    write_jsonl(heldout_attack_pairs(heldout_split, args.seed, args.heldout_attack_per_tag),
                args.out_dir / "heldout_attacks_v2.jsonl")

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
