# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""문서 성격별 **보고용** 세트(#456) — 조정용 `doc_types.py`와 문서 틀·이름 음절이 다르다.

조정용(`doc_types_v1`)은 미탐 예를 이슈에 올려 core 규칙을 고치는 데 이미 썼다(#662·#663). 그 세트로
정확도를 보고하면 시험 문제를 보고 공부한 점수가 된다. 그래서 같은 다섯 종류(판결문·상담 기록·사내 메일·
회의록·명단)를 **문서 틀부터 새로 쓴** 세트를 따로 둔다.

- 틀: 조정용에 없는 문서 꼴을 쓴다(가처분 결정문·항소심 판결, 민원 상담 일지·채팅 상담, 회신 메일·공지 메일,
  표 회의록·위원회 회의록, 탭·세미콜론 명단).
- 이름: 이름 음절을 조정용·학습 데이터(`entities._GIVEN_SYLLABLES`)와 겹치지 않게 골랐다. 학습한 기본 모델이
  외운 이름으로 점수를 얻지 못하게 하려는 것이다. 성은 실제 분포처럼 흔한 성을 주로 쓰고 덜 흔한 성을 섞는다.
- 문서 안의 모든 개인정보에 라벨을 붙이고, 이름처럼 보이는 일반 낱말(직함·사건명·부서명)에는 붙이지 않는다.

**이 세트의 미탐 예를 보고 규칙을 고치지 않는다.** 규칙은 조정용 세트로 고치고, 이 세트는 집계 숫자만 본다.
"""

from __future__ import annotations

import random

from bench.generator.doc_types import _Doc, _josa, _value
from bench.generator.entities import _SURNAMES

# 조정용·학습 데이터의 이름 음절(entities._GIVEN_SYLLABLES)과 겹치지 않는 흔한 이름 음절.
# 겹치지 않는지는 bench/tests/test_doc_types_holdout.py가 확인한다.
_HOLDOUT_SYLLABLES = [
    "태", "동", "상", "철", "미", "소", "나", "유", "시", "다",
    "채", "승", "희", "주", "용", "기", "혁", "선", "보", "라",
    "온", "겸", "슬", "린", "람", "솔", "결", "별", "담", "형",
]
# entities._SURNAMES 다음으로 흔한 성. 다섯 명에 한 명꼴로 섞는다.
_MORE_SURNAMES = ["류", "차", "구", "우", "주", "나", "민", "진", "지", "엄"]

# 성 + 한 음절이 흔한 낱말과 같은 두 글자 이름은 뽑지 않는다. "피고인 정보"처럼 사람이 읽어도 이름인지
# 헷갈리는 문장이 생겨 세트가 불공정해진다. 실제로 있을 법한 이름보다 낱말 뜻이 훨씬 흔한 것만 넣었다.
_WORD_LIKE_NAMES = frozenset({
    "이동", "이상", "이미", "이유", "이용", "이기", "이슬", "이다", "이주", "이별", "이온",
    "정상", "정기", "정보", "정승", "강철", "조상", "조미", "조용", "조기", "조선", "조형",
    "장미", "장소", "장기", "장보", "장담", "한미", "한시", "한다", "한주", "한기", "한라", "한결",
    "오시", "오다", "오용", "오기", "오보", "서다", "서기", "신동", "신상", "신나", "신다", "신용",
    "신기", "신선", "신라", "신형", "권유", "황동", "황소", "안동", "안다", "안주", "안기", "안보",
    "송별", "전동", "전철", "전시", "전승", "전주", "전용", "전기", "전선", "전라", "전담", "전형",
    "홍시", "홍채", "홍보", "유동", "유상", "유용", "유기", "유선", "유보", "유별", "유형",
    "고철", "고소", "고유", "고시", "고용", "고기", "고온", "양상", "양주", "양보", "양형",
    "손상", "손주", "배상", "배기", "배선", "백미", "백주", "허상", "허나", "허다", "허용", "허기",
    "남동", "남미", "남다", "남용", "남기", "심상", "심다", "심기", "박동", "최상", "최소", "최다",
    "최선", "임상", "임시", "임용", "임기", "주유", "주기", "주선", "주소", "주시", "나라", "지상",
    "지주", "지시", "지형", "우동", "우유", "우상", "우주", "우선", "우승", "구동", "구상", "구미",
    "구형", "구별", "구슬", "차주", "차기", "차선", "차다", "차용", "민주", "진동", "진상", "진주",
    "진보", "엄선",
})

_FIRMS = ["해든", "새벽", "고운", "바른숲", "늘품"]
_DEPTS = ["총무팀", "회계팀", "기획팀", "품질관리팀", "고객지원팀"]


def _name(rng: random.Random) -> str:
    """성 + 이름. 세 글자를 주로, 두 글자를 15% 섞는다(조정용과 같은 비율)."""
    while True:
        surname = rng.choice(_MORE_SURNAMES) if rng.random() < 0.2 else rng.choice(_SURNAMES)
        given = 1 if rng.random() < 0.15 else 2
        name = surname + "".join(rng.sample(_HOLDOUT_SYLLABLES, k=given))
        if name not in _WORD_LIKE_NAMES:
            return name


def _names(rng: random.Random, n: int) -> list[str]:
    out: list[str] = []
    while len(out) < n:
        name = _name(rng)
        if name not in out:
            out.append(name)
    return out


def _day(rng: random.Random) -> str:
    return f"2025. {rng.randint(1, 12)}. {rng.randint(1, 28)}."


# ── 판결문 ──────────────────────────────────────────────────────────


def gen_injunction_decision(rng: random.Random) -> _Doc:
    """가처분 결정문 — 채권자·채무자, 참고인, 합의부 판사 셋."""
    creditor, debtor, lawyer, witness, j1, j2, j3 = _names(rng, 7)
    d = _Doc().add(f"서울동부지방법원\n결 정\n\n사건 2025카합{rng.randint(10000, 99999)} 업무방해금지가처분\n채권자 ")
    d.pii("name", creditor).add("\n       ").pii("address", _value("address", rng))
    d.add("\n       대리인 변호사 ").pii("name", lawyer).add("\n채무자 ").pii("name", debtor)
    d.add("\n       ").pii("address", _value("address", rng))
    d.add("\n\n주 문\n채무자는 채권자가 운영하는 매장 앞에서 확성기를 사용하여서는 아니 된다.\n\n이 유\n")
    d.add("기록에 의하면 채무자 ").pii("name", debtor).add(_josa(debtor, "이", "가"))
    d.add(f" {_day(rng)}부터 매장 앞에서 소음을 낸 사실이 소명된다. 참고인 ").pii("name", witness)
    d.add(_josa(witness, "이", "가")).add(" 낸 사실확인서도 이에 부합한다.\n\n")
    d.add(f"{_day(rng)}\n재판장 판사 ").pii("name", j1).add("\n       판사 ").pii("name", j2)
    d.add("\n       판사 ").pii("name", j3)
    return d


def gen_appeal_judgment(rng: random.Random) -> _Doc:
    """형사 항소심 판결 — 검사 둘, 법무법인 담당변호사, 피해 회사 대표."""
    accused, p1, p2, lawyer, ceo, witness = _names(rng, 6)
    d = _Doc().add(f"대전지방법원 제1형사부\n판 결\n\n사건 2025노{rng.randint(1000, 9999)} 업무상횡령\n피고인 ")
    d.pii("name", accused).add(" (").pii("rrn", _value("rrn", rng)).add("), 회사원\n항소인 피고인\n검사 ")
    d.pii("name", p1).add("(기소), ").pii("name", p2).add("(공판)\n변호인 법무법인 ")
    d.add(f"{rng.choice(_FIRMS)} 담당변호사 ").pii("name", lawyer)
    d.add("\n\n주 문\n피고인의 항소를 기각한다.\n\n이 유\n1. 항소이유의 요지\n")
    d.add("피고인은 원심의 형이 너무 무거워 부당하다고 주장한다.\n2. 판단\n피고인이 피해 회사 대표 ")
    d.pii("name", ceo).add("에게 피해액 일부를 갚은 점, 원심 증인 ").pii("name", witness)
    d.add(_josa(witness, "이", "가")).add(" 피고인의 사정을 진술한 점을 모두 살펴도 원심의 형은 적정하다.")
    return d


# ── 상담 기록 ──────────────────────────────────────────────────────


def gen_civil_complaint_log(rng: random.Random) -> _Doc:
    """구청 민원 상담 일지 — 칸이 있는 서식과 상담 요지."""
    citizen, officer, neighbor, officer2 = _names(rng, 4)
    d = _Doc().add(f"민원 상담 일지\n접수번호: 2025-{rng.randint(10000, 99999)}\n민원인 성명: ")
    d.pii("name", citizen).add("    연락처: ").pii("phone", _value("phone", rng))
    d.add("\n주소: ").pii("address", _value("address", rng)).add("\n담당 주무관: ").pii("name", officer)
    d.add("\n상담 요지: 민원인은 이웃 주민 ").pii("name", neighbor)
    d.add(" 씨와의 주차 문제로 여러 차례 다퉜다며 중재를 요청함.\n조치 결과: ").pii("name", officer2)
    d.add(" 주무관이 현장을 확인한 뒤 양측에 안내문을 보냄.")
    return d


def gen_chat_support(rng: random.Random) -> _Doc:
    """채팅 상담 기록 — 시각, 말한 사람 표시, 말 속의 이름."""
    agent, customer, spouse = _names(rng, 3)
    h = rng.randint(9, 17)
    d = _Doc().add(f"[채팅 상담 기록]\n[{h}:02] ").pii("name", agent).add("(상담사): 문의 주셔서 감사합니다.\n")
    d.add(f"[{h}:03] 고객: ").pii("name", customer).add("인데요, 환불 문의드려요.\n")
    d.add(f"[{h}:04] ").pii("name", agent).add("(상담사): ").pii("name", customer)
    d.add(" 님, 주문번호를 알려 주시겠어요?\n")
    d.add(f"[{h}:06] 고객: 남편 ").pii("name", spouse).add(" 명의로 주문했어요. 메일은 ")
    d.pii("email", _value("email", rng)).add("이에요.")
    return d


# ── 사내 메일 ──────────────────────────────────────────────────────


def gen_reply_email(rng: random.Random) -> _Doc:
    """회신 메일 — 받는 이 호칭, 서명 칸, 아래에 원문 머리."""
    partner, sender, staff = _names(rng, 3)
    d = _Doc().pii("name", partner).add(" 님께,\n\n보내 주신 견적서 잘 받았습니다. 검토한 뒤 다음 주 중으로 회신드리겠습니다.\n")
    d.add("실무 문의는 ").pii("name", staff).add(" 매니저에게 주셔도 됩니다.\n\n").pii("name", sender)
    d.add(f" 올림\n{rng.choice(_DEPTS)} | {rng.choice(_FIRMS)} 주식회사\n전화 ").pii("phone", _value("phone", rng))
    d.add("\n\n-----Original Message-----\nFrom: ").pii("name", partner).add(" <").pii("email", _value("email", rng))
    d.add(">\nTo: ").pii("name", sender).add("\nSubject: 견적서 송부의 건")
    return d


def gen_notice_email(rng: random.Random) -> _Doc:
    """전체 공지 메일 — 주차별 당직자 목록과 문의처."""
    a, b, c, admin = _names(rng, 4)
    d = _Doc().add("제목: [공지] 다음 달 당직 근무 안내\n수신: 전 직원\n발신: 총무팀\n\n")
    d.add("다음 달 당직은 아래와 같이 운영합니다.\n- 1주차: ").pii("name", a).add(", ").pii("name", b)
    d.add("\n- 2주차: ").pii("name", c).add("\n바꿔야 하면 총무팀 ").pii("name", admin)
    d.add("에게 미리 알려 주세요.")
    return d


# ── 회의록 ──────────────────────────────────────────────────────────


def gen_weekly_table_minutes(rng: random.Random) -> _Doc:
    """주간 회의 — 참석·불참, 마크다운 표, 후속 조치."""
    lead, b, c, absent = _names(rng, 4)
    d = _Doc().add(f"[주간 업무 회의] {_day(rng)}\n참석: ").pii("name", lead).add("(팀장), ").pii("name", b)
    d.add(", ").pii("name", c).add("\n불참: ").pii("name", absent).add("(휴가)\n\n| 담당 | 진행 내용 | 기한 |\n|---|---|---|\n| ")
    d.pii("name", lead).add(" | 예산안 검토 | 다음 주 |\n| ").pii("name", b).add(" | 거래처 방문 | 이번 주 |\n\n")
    d.add("후속 조치: ").pii("name", c).add(" 매니저가 회의 자료를 공유한다.\n기록: ").pii("name", b)
    return d


def gen_committee_minutes(rng: random.Random) -> _Doc:
    """위원회 회의록 — 위원장·간사·위원 발언과 서명."""
    chair, secretary, m1, m2 = _names(rng, 4)
    d = _Doc().add(f"제{rng.randint(2, 9)}차 운영위원회 회의록\n\n1. 개회: 위원장 ").pii("name", chair)
    d.add(_josa(chair, "이", "가")).add(" 성원을 확인하고 개회를 선언함.\n2. 보고: 간사 ").pii("name", secretary)
    d.add(_josa(secretary, "이", "가")).add(" 지난 회의 결과를 보고함.\n3. 심의: ").pii("name", m1)
    d.add(" 위원은 예산 집행 시기를 늦추자는 의견을 냈고, ").pii("name", m2).add(" 위원은 이에 동의함.\n")
    d.add("4. 폐회\n\n위원장 ").pii("name", chair).add(" (서명)")
    return d


# ── 명단 ────────────────────────────────────────────────────────────


def gen_tsv_roster(rng: random.Random) -> _Doc:
    """탭으로 나눈 직원 명단 — 번호·성명·직위·이메일."""
    d = _Doc().add("No\t성명\t직위\t이메일\n")
    for i, name in enumerate(_names(rng, rng.randint(3, 6)), start=1):
        if i > 1:
            d.add("\n")
        d.add(f"{i}\t").pii("name", name).add(f"\t{rng.choice(['사원', '주임', '선임', '책임'])}\t")
        d.pii("email", _value("email", rng))
    return d


def gen_semicolon_roster(rng: random.Random) -> _Doc:
    """세미콜론으로 나눈 담당자 명단 — 사번·담당자·휴대전화·비고."""
    d = _Doc().add("사번;담당자;휴대전화;비고\n")
    for i, name in enumerate(_names(rng, rng.randint(3, 6))):
        if i:
            d.add("\n")
        d.add(f"A{rng.randint(1000, 9999)};").pii("name", name).add(";").pii("phone", _value("phone", rng))
        d.add(";" + rng.choice(["", "재택", "출장 중", "육아휴직"]))
    return d


HOLDOUT_DOC_TYPES = {
    "judgment": (gen_injunction_decision, gen_appeal_judgment),
    "counseling": (gen_civil_complaint_log, gen_chat_support),
    "email": (gen_reply_email, gen_notice_email),
    "minutes": (gen_weekly_table_minutes, gen_committee_minutes),
    "roster": (gen_tsv_roster, gen_semicolon_roster),
}


def generate_holdout_dataset(seed: int, per_type: int = 40) -> list[dict]:
    """종류마다 per_type건씩. 행마다 split="holdout"을 달아 조정용과 섞이지 않게 한다."""
    rows = []
    for doc_type in sorted(HOLDOUT_DOC_TYPES):
        rng = random.Random(f"{seed}:{doc_type}")
        gens = HOLDOUT_DOC_TYPES[doc_type]
        for i in range(per_type):
            doc = gens[i % len(gens)](rng)
            rows.append({"text": doc.text, "labels": doc.labels, "difficulty": "doc", "doc_type": doc_type, "split": "holdout"})
    return rows
