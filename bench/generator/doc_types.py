# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""문서 성격별 이름 평가 세트(#661) — 판결문·상담 기록·사내 메일·회의록·엑셀 명단.

이름이 개인정보인지는 문서 성격에 따라 달라진다(2026-10-04 멘토링). 이름만 적힌 명단보다
판결문처럼 사건·역할과 함께 이름이 여러 번 나오는 문서에서 이름을 놓치는 게 더 위험하다.
synth_v1·v2는 업무 문장 한두 줄짜리라 문서 종류를 구분하지 않아, 종류별로 어디가 약한지
숫자로 말할 수 없었다.

문서마다 그 종류에 흔한 틀(판결문의 당사자 표시·이유, 메일의 받는 사람·맺음말 등)을 새로 쓰고,
값(이름·연락처·주소)은 시드로 뽑는다. 문서 안의 **모든** 개인정보에 정답 라벨을 붙여
precision도 의미가 있게 한다. "피고 회사", "원고 측"처럼 이름 자리에 오는 일반 낱말과 법인명은
라벨을 붙이지 않는다 — 이걸 이름으로 가리면 오탐으로 집계된다.

이 세트는 core 규칙을 맞추려는 게 아니라 문서 종류별 약점을 보는 측정용이다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from bench.generator.entities import _GIVEN_SYLLABLES, _SURNAMES, generate_entity


@dataclass
class _Doc:
    """조각을 이어 붙이면서 개인정보 자리의 라벨 위치를 센다."""

    text: str = ""
    labels: list[dict] = field(default_factory=list)

    def add(self, piece: str) -> _Doc:
        self.text += piece
        return self

    def pii(self, kind: str, value: str) -> _Doc:
        self.labels.append({"kind": kind, "start": len(self.text), "end": len(self.text) + len(value)})
        self.text += value
        return self


def _has_batchim(char: str) -> bool:
    """한글 음절에 받침이 있는지. 음절 코드를 28로 나눈 나머지가 종성 번호다."""
    return (ord(char) - 0xAC00) % 28 != 0


def _josa(word: str, with_batchim: str, without: str) -> str:
    """받침에 맞는 조사(이/가, 은/는, 과/와)를 고른다."""
    return with_batchim if _has_batchim(word[-1]) else without


def _name(rng: random.Random) -> str:
    """성 + 이름. 실제 분포처럼 세 글자를 주로, 두 글자(성 + 한 글자)를 15% 섞는다."""
    given = 1 if rng.random() < 0.15 else 2
    return rng.choice(_SURNAMES) + "".join(rng.sample(_GIVEN_SYLLABLES, k=given))


def _names(rng: random.Random, n: int) -> list[str]:
    """서로 다른 이름 n개 — 한 문서에서 같은 이름이 다른 사람으로 나오지 않게 한다."""
    out: list[str] = []
    while len(out) < n:
        name = _name(rng)
        if name not in out:
            out.append(name)
    return out


def _value(kind: str, rng: random.Random) -> str:
    return generate_entity(kind, rng, "easy").text


def _date(rng: random.Random) -> str:
    """판결·회의 날짜(개인정보 아님). 생년월일 단서 없이 쓴다."""
    return f"2025. {rng.randint(1, 12)}. {rng.randint(1, 28)}."


# 지어낸 법인·기관 이름. 개인정보가 아니라 라벨을 붙이지 않는다.
_FIRMS = ["한빛", "새솔", "가온", "누리", "다온", "미르"]
_TITLES = ["팀장", "과장", "대리", "부장", "차장", "실장"]
_DEPTS = ["영업팀", "인사팀", "재무팀", "개발팀", "구매팀"]


# ── 판결문 ──────────────────────────────────────────────────────────


def gen_judgment_civil(rng: random.Random) -> _Doc:
    """민사 판결문 — 당사자 표시, 주문, 이유, 판사 서명."""
    plaintiff, defendant, lawyer, witness, judge = _names(rng, 5)
    firm = rng.choice(_FIRMS)
    d = _Doc().add(f"서울중앙지방법원\n판 결\n\n사건 2025가합{rng.randint(10000, 99999)} 손해배상(기)\n원고 ")
    d.pii("name", plaintiff).add("\n    ").pii("address", _value("address", rng))
    d.add("\n원고 소송대리인 변호사 ").pii("name", lawyer)
    d.add("\n피고 ").pii("name", defendant)
    d.add(f"\n피고 소송대리인 법무법인 {firm}\n변론종결 {_date(rng)}\n\n주 문\n")
    d.add(f"1. 피고는 원고에게 {rng.randint(1, 90) * 1000000:,}원을 지급하라.\n2. 원고의 나머지 청구를 기각한다.\n\n이 유\n")
    d.add("1. 기초사실\n가. 원고 ").pii("name", plaintiff).add(_josa(plaintiff, "은", "는"))
    d.add(f" {_date(rng)} 피고 ").pii("name", defendant).add(_josa(defendant, "과", "와"))
    d.add(" 사이에 물품공급계약을 체결하였다.\n나. 증인 ").pii("name", witness)
    d.add("의 증언에 의하면, 피고는 약정한 기일까지 물품을 공급하지 않았다.\n")
    d.add("2. 판단\n피고 측은 원고 측의 귀책사유를 주장하나, 피고 ").pii("name", defendant)
    d.add("의 주장은 이유 없다.\n\n판사 ").pii("name", judge)
    return d


def gen_judgment_criminal(rng: random.Random) -> _Doc:
    """형사 판결문 — 피고인·피해자·검사·변호인, 범죄사실."""
    accused, victim, prosecutor, counsel, judge = _names(rng, 5)
    d = _Doc().add(f"수원지방법원\n판 결\n\n사건 2025고단{rng.randint(1000, 9999)} 사기\n피고인 ")
    d.pii("name", accused).add(" (").pii("rrn", _value("rrn", rng)).add(")\n    주거 ").pii("address", _value("address", rng))
    d.add("\n검사 ").pii("name", prosecutor).add("(기소, 공판)\n변호인 변호사 ").pii("name", counsel)
    d.add(f"\n\n주 문\n피고인을 징역 {rng.randint(6, 36)}월에 처한다.\n\n이 유\n범죄사실\n피고인 ")
    d.pii("name", accused).add(_josa(accused, "은", "는"))
    d.add(f" {_date(rng)} 피해자 ").pii("name", victim).add("에게 투자금을 돌려줄 의사나 능력이 없음에도")
    d.add(" 원금을 보장한다고 거짓말하여 이를 송금받았다.\n증거의 요지\n1. 피해자 ").pii("name", victim)
    d.add("의 진술서\n1. 피고인의 일부 법정진술\n\n판사 ").pii("name", judge)
    return d


# ── 상담 기록 ──────────────────────────────────────────────────────


def gen_counseling_log(rng: random.Random) -> _Doc:
    """고객센터 상담 기록 — 서식 칸과 자유 서술이 섞인다."""
    agent, customer, guardian, agent2 = _names(rng, 4)
    d = _Doc().add(f"[상담 기록] 2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d} {rng.randint(9, 17)}:{rng.randint(0, 59):02d}\n")
    d.add("상담원: ").pii("name", agent).add("\n고객명: ").pii("name", customer)
    d.add("\n연락처: ").pii("phone", _value("phone", rng))
    d.add("\n내용: ").pii("name", customer).add(" 고객님께서 배송 지연을 문의하심. 보호자 ")
    d.pii("name", guardian).add("님과 통화 후 재발송 처리 예정.\n처리: ").pii("name", agent2).add(" 상담원에게 이관")
    return d


def gen_counseling_dialog(rng: random.Random) -> _Doc:
    """통화 녹취를 옮긴 대화 — 이름이 말 속에 나온다."""
    agent, customer = _names(rng, 2)
    d = _Doc().add("상담원: 안녕하세요, 고객센터 ").pii("name", agent).add("입니다. 무엇을 도와드릴까요?\n")
    d.add("고객: 네, 제 이름은 ").pii("name", customer).add(_josa(customer, "이고요", "고요"))
    d.add(", 지난주에 주문한 상품이 아직 안 왔어요.\n상담원: ").pii("name", customer)
    d.add(" 고객님, 확인해 보니 내일 도착 예정입니다. 연락처 ").pii("phone", _value("phone", rng))
    d.add("로 안내 문자 드리겠습니다.")
    return d


# ── 사내 메일 ──────────────────────────────────────────────────────


def gen_internal_email(rng: random.Random) -> _Doc:
    """사내 메일 — 받는 사람·참조 머리, 호칭, 맺음말."""
    to, cc, sender, other = _names(rng, 4)
    t1, t2 = rng.sample(_TITLES, k=2)
    d = _Doc().add("받는 사람: ").pii("name", to).add(" <").pii("email", _value("email", rng)).add(">\n")
    d.add("참조: ").pii("name", cc).add(f" {t2}\n제목: 3분기 정산 자료 송부\n\n")
    d.pii("name", to).add(f" {t1}님, 안녕하세요.\n{rng.choice(_DEPTS)} ").pii("name", sender).add("입니다.\n")
    d.add("지난주 ").pii("name", other).add(" 대리님께서 요청하신 정산 자료를 첨부드립니다.\n")
    d.add("확인 부탁드립니다.\n\n감사합니다.\n").pii("name", sender).add(" 드림")
    return d


# ── 회의록 ──────────────────────────────────────────────────────────


def gen_meeting_minutes(rng: random.Random) -> _Doc:
    """회의록 — 참석자 나열, 작성자, 안건별 발언자."""
    a, b, c, writer = _names(rng, 4)
    ta, tb, tc = (rng.choice(_TITLES) for _ in range(3))
    d = _Doc().add(f"회의록\n일시: {_date(rng)} 14:00\n장소: 3층 대회의실\n참석자: ")
    d.pii("name", a).add(", ").pii("name", b).add(", ").pii("name", c).add("\n작성자: ").pii("name", writer)
    d.add("\n\n1. ").pii("name", a).add(f" {ta}{_josa(ta, '이', '가')} 3분기 실적을 보고함.\n2. ")
    d.pii("name", b).add(f" {tb}{_josa(tb, '은', '는')} 신규 거래처 계약 건을 설명함.\n")
    d.add("결정 사항: 다음 회의는 ").pii("name", c).add(f" {tc}{_josa(tc, '이', '가')} 주관한다.")
    return d


# ── 엑셀(CSV) 명단 ─────────────────────────────────────────────────


def gen_csv_roster(rng: random.Random) -> _Doc:
    """엑셀에서 내보낸 명단 — 머리행 아래로 이름·부서·연락처가 이어진다."""
    d = _Doc().add(rng.choice(["이름", "성명"]) + ",부서,연락처,입사일\n")
    for i, name in enumerate(_names(rng, rng.randint(3, 6))):
        if i:
            d.add("\n")
        d.pii("name", name).add(f",{rng.choice(_DEPTS)},").pii("phone", _value("phone", rng))
        d.add(f",20{rng.randint(10, 25)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}")
    return d


# 문서 종류 → 생성 함수들. 한 종류에 틀이 둘이면 번갈아 쓴다.
DOC_TYPES = {
    "judgment": (gen_judgment_civil, gen_judgment_criminal),
    "counseling": (gen_counseling_log, gen_counseling_dialog),
    "email": (gen_internal_email,),
    "minutes": (gen_meeting_minutes,),
    "roster": (gen_csv_roster,),
}


def generate_doc_types_dataset(seed: int, per_type: int = 40) -> list[dict]:
    """종류마다 per_type건씩, 항상 같은 시드로 재현 가능하게 만든다."""
    rows = []
    for doc_type in sorted(DOC_TYPES):
        rng = random.Random(f"{seed}:{doc_type}")
        gens = DOC_TYPES[doc_type]
        for i in range(per_type):
            doc = gens[i % len(gens)](rng)
            rows.append({"text": doc.text, "labels": doc.labels, "difficulty": "doc", "doc_type": doc_type})
    return rows
