"""문장 템플릿에 개인정보 값을 심어 문서(JSONL 한 줄)를 만든다.

동작 원리:
1. 템플릿 문자열의 {kind} 자리표시자를 순서대로 찾는다.
2. 각 자리표시자를 entities.generate_entity()가 만든 값으로 치환하면서
   현재까지 조립된 텍스트 길이로 start/end(파이썬 슬라이스 규약)를 계산한다.
3. 치환이 끝난 전체 텍스트와 라벨 목록을 함께 반환한다 — bench/README.md의 데이터셋 포맷 계약을 따른다.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from bench.generator.distractors import generate_distractor
from bench.generator.entities import ALL_KINDS, generate_entity

# distractor는 개인정보가 아니므로 라벨을 붙이지 않는다 — _NON_LABEL_KINDS에서 분기 처리.
_PLACEHOLDER_RE = re.compile(r"\{(name|phone|email|rrn|address|card|biz_reg|passport|account|distractor)\}")
_NON_LABEL_KINDS = frozenset({"distractor"})

# 개인정보가 실제로 포함된 템플릿 — 다양한 업무 맥락(고객센터/병원/학교/관공서/인사/배송/금융)을 커버한다.
_TEMPLATES = [
    "고객 {name}님 {phone}로 연락 부탁드립니다.",
    "신청자: {name} / 연락처: {phone} / 이메일: {email}",
    "{name} 환자분, 주민등록번호 {rrn} 확인되었습니다.",
    "배송지: {address} (수령인 {name}, {phone})",
    "{email}로 회신 주시면 {name} 담당자가 답변드립니다.",
    "긴급 연락처 {phone}, 자택 주소는 {address}입니다.",
    "본인확인용 주민번호 {rrn}와 이메일 {email}을 제출합니다.",
    "안녕하세요, 저는 {name}이고 전화번호는 {phone}입니다.",
    "{address}에 거주하는 {name}님께 우편을 발송했습니다.",
    "오늘 회의록: 작성자 {name}, 문의는 {email}로.",
    # 병원/의료
    "환자명 {name}, 주민번호 {rrn}, 보호자 연락처 {phone}로 등록되었습니다.",
    "{name} 님의 진료 예약이 확정되었습니다. 문의: {phone}",
    # 학교/교육
    "학생 {name}(학부모 연락처 {phone})의 결석계가 접수되었습니다.",
    "{name} 선생님께 {email}로 성적 자료를 전달했습니다.",
    # 관공서/행정
    "민원인 {name}님, 주민등록번호 {rrn}로 접수된 건 처리 완료되었습니다. 회신 주소: {address}",
    "전입신고 대상자: {name}, 신주소: {address}, 연락처: {phone}",
    # 인사/채용
    "지원자 {name} 이력서 접수 — 연락처 {phone}, 이메일 {email}",
    "신규 입사자 {name}님의 4대보험 등록을 위해 주민번호 {rrn}가 필요합니다.",
    # 택배/배송
    "{name}님 앞, {address}로 배송 중입니다. 수령 전 {phone}로 연락드릴 수 있습니다.",
    "반품 신청자 {name}, 환불 계좌 확인을 위해 연락처 {phone}를 남겨주세요.",
    # 금융/보험
    "가입자 {name}, 주민번호 {rrn} 기준으로 보험료가 산정되었습니다.",
    "{name}님의 이체 알림: 문의는 {phone} 또는 {email}로 부탁드립니다.",
    # 결제/환불 (카드번호)
    "{name}님 카드번호 {card}로 결제가 완료되었습니다.",
    "환불 처리를 위해 {name}님의 카드번호 {card}를 확인했습니다. 문의: {phone}",
    "정기결제 등록: 카드 {card}, 명의자 {name}, 연락처 {phone}",
    "{card} 카드로 결제 시도가 감지되어 {name}님께 {phone}로 확인 연락드립니다.",
    # 한 문서에 같은 종류가 두 번 등장하는 경우 (담당자 교체, 자택/직장 번호 등)
    "담당자가 {name}에서 {name}으로 변경되었습니다. 새 연락처: {phone}",
    "자택 {phone}, 직장 {phone} 두 번호 모두 등록해 주세요.",
    # 실제 개인정보 + 헷갈리는 값이 섞인 템플릿 — 엔진이 distractor까지 잘못 잡아내지 않는지 확인.
    "주문번호 {distractor}, 고객 {name}님 {phone}로 발송 예정입니다.",
    "사업자등록번호 {distractor} / 담당자 {name} / 이메일 {email}",
    "결제 금액 {distractor}, 영수증은 {email}로 발송됩니다.",
    # 사업자·거래 문서 (사업자등록번호)
    "거래처 사업자등록번호 {biz_reg}, 담당자 {name}, 연락처 {phone}",
    "세금계산서 발행을 위해 사업자등록번호 {biz_reg}를 확인했습니다. 문의: {phone}",
    "계약서상 사업자등록번호는 {biz_reg}이며, 서명자는 {name}입니다.",
    # 명함/채용공고 — 동/번지 없이 시/도(+구)까지만 나오는 부분 주소가 흔하다(#195).
    "채용 공고 - 근무지: {address}. 문의: {phone}",
    "본사는 {address}에 위치하며, 담당자는 {name}입니다.",
    # 출입국/비자 (여권번호) — "여권"이 앞 15자 안에 있어 core가 확신도 0.9로 잡는 케이스.
    "여권번호 {passport}로 출입국 기록을 조회했습니다.",
    "출입국 심사대에서 {name}님의 여권번호 {passport}를 확인했습니다.",
    "비자 신청자 {name}, 여권번호는 {passport}이며 연락처는 {phone}입니다.",
    # 문맥어 없이 번호만 나오는 케이스 — core가 확신도 0.6(형식만)으로 잡아야 정상.
    "해외 출장 등록 코드는 {passport}입니다.",
    # 외국인등록번호(rrn 성별코드 5~8) — core RRNDetector가 내국인과 동일한 규칙으로 잡는다(#148).
    "외국인등록번호 {rrn}로 체류 자격을 확인했습니다.",
    "{name}님의 외국인등록번호는 {rrn}이며, 담당자는 {phone}로 연락드립니다.",
    # 계좌번호(account) — core AccountDetector는 문맥어(계좌/입금/이체/은행/뱅크 등)가 매치
    # 앞뒤 15자 안에 없으면 아예 탐지하지 않는 하드 게이트라(#180), 모든 positive 템플릿에
    # 문맥어를 반드시 포함한다.
    "환불 계좌번호는 {account}이며, 예금주는 {name}입니다.",
    "{name}님 앞으로 {account} 계좌에 입금 완료했습니다.",
    "이체할 계좌: {account}, 은행 확인 부탁드립니다.",
    "신한은행 {account}로 송금 부탁드립니다. 문의는 {phone}로.",
    # "정산 담당자"는 쓰지 않는다 — "정"이 성씨라 "정산" 자체가 이름 후보가 되고 바로 뒤
    # "담당자"가 존칭 단서로 잡혀 오탐이 난다(직접 재현 확인, #180). "출금"은 성씨가 아니라 안전하다.
    "출금 담당자 {name}, 계좌는 {account}입니다.",
    # 인사/계약 — 역할어·존칭 없이 직함만 붙는 이름(#213). core는 3글자 이상 풀네임만 이
    # 단서 하나로 인정한다 — 2음절 이름(성씨+1음절)은 설계상 여전히 놓친다(아래 confidence 절 참고).
    "{name} 대표가 계약서에 서명했습니다.",
    "{name} 팀장이 프로젝트 현황을 보고했습니다.",
    "{name} 부장님께 서류를 전달했습니다.",
]

# 개인정보가 전혀 없는(또는 distractor만 있는) 템플릿 — 정답 라벨이 0개인 문서를 만든다.
# false positive(오탐) 측정용: core가 여기서 뭔가를 개인정보로 잘못 찾아내면 그대로 FP로 집계된다.
_NEGATIVE_TEMPLATES = [
    "회의는 내일 오후 2시에 진행됩니다.",
    "이번 분기 매출 목표는 지난해 대비 12% 증가입니다.",
    "서버 점검은 매주 화요일 새벽에 진행됩니다.",
    "주문번호 {distractor}가 정상 접수되었습니다.",
    "사업자등록번호는 {distractor}이며, 배송지 우편번호는 {distractor}입니다.",
    "결제일 {distractor}, 결제 금액 {distractor}.",
    "송장번호 {distractor}로 배송이 시작되었습니다.",
    "다음 회의 안건은 예산 검토와 일정 조정입니다.",
    # 여권번호 형식과 자릿수만 다른 사원번호·상품 코드 (#145)
    "사원번호 {distractor}로 출입 기록이 등록되었습니다.",
    "재고 관리 시스템에 상품 코드 {distractor}를 등록했습니다.",
    "로트번호 {distractor} 제품의 검수가 완료되었습니다.",
    # 부서·업무어가 직함 앞에 와서 이름으로 오탐되면 안 되는 케이스(#213 core 이슈 예시 그대로).
    # "구매"(구=성씨)·"정기"(정=성씨)·"홍보"(홍=성씨) — 전부 2음절이라 직함 단서 하나만으론
    # core가 이름으로 인정하지 않아야 정상이다(성+2자 풀네임만 인정하는 가드).
    "구매 부장이 결재했습니다.",
    "정기 이사가 참석했습니다.",
    "홍보 사원이 채용되었습니다.",
]


@dataclass(frozen=True)
class Label:
    kind: str
    start: int
    end: int


@dataclass(frozen=True)
class Document:
    text: str
    labels: list[Label]
    difficulty: str  # "easy" | "hard" | "mixed" | "negative"


def _render(template: str, rng: random.Random, difficulty: str) -> Document:
    """템플릿의 {kind} 자리표시자를 채우고, 개인정보 종류만 라벨로 기록한다.

    {distractor}는 개인정보가 아니므로 텍스트에는 삽입하되 라벨은 남기지 않는다 —
    core가 이 구간을 잘못 탐지하면 evaluate.py에서 그대로 FP(오탐)로 집계된다.
    """
    text_parts: list[str] = []
    labels: list[Label] = []
    cursor = 0
    last_end = 0
    for m in _PLACEHOLDER_RE.finditer(template):
        text_parts.append(template[last_end : m.start()])
        cursor += m.start() - last_end

        kind = m.group(1)
        value = generate_distractor(rng) if kind in _NON_LABEL_KINDS else generate_entity(kind, rng, difficulty).text
        start = cursor
        text_parts.append(value)
        cursor += len(value)
        if kind not in _NON_LABEL_KINDS:
            labels.append(Label(kind=kind, start=start, end=cursor))

        last_end = m.end()

    text_parts.append(template[last_end:])
    return Document(text="".join(text_parts), labels=labels, difficulty=difficulty)


def generate_document(rng: random.Random, template: str | None = None, difficulty: str | None = None) -> Document:
    """실제 개인정보가 포함된 합성 문서 하나를 만든다 (정답 라벨 1개 이상).

    difficulty가 None이면 "easy"/"hard" 중 하나를 무작위로 골라 문서 전체에 일관되게 적용한다
    (entities.generate_entity의 difficulty 파라미터로 표기 형식을 제어 — entities.py 참고).
    """
    resolved_difficulty = difficulty if difficulty is not None else rng.choice(["easy", "hard"])
    return _render(template if template is not None else rng.choice(_TEMPLATES), rng, resolved_difficulty)


def generate_multi_sentence_document(
    rng: random.Random, sentence_count: int | None = None, difficulty: str | None = None
) -> Document:
    """여러 문장을 이어붙인 복합 문서 하나를 만든다 (정답 라벨 2개 이상 문장에 걸쳐 분포).

    실제 문서는 한 문장으로 끝나지 않는다 — 문장 여러 개를 이어붙여도 뒤 문장의 라벨
    start/end가 앞 문장들의 길이만큼 밀린 위치를 정확히 가리키는지(오프셋 정합성)를 검증한다.
    """
    resolved_difficulty = difficulty if difficulty is not None else rng.choice(["easy", "hard"])
    n = sentence_count if sentence_count is not None else rng.choice([2, 3])

    text_parts: list[str] = []
    labels: list[Label] = []
    cursor = 0
    for i in range(n):
        if i > 0:
            text_parts.append(" ")
            cursor += 1
        sentence = _render(rng.choice(_TEMPLATES), rng, resolved_difficulty)
        text_parts.append(sentence.text)
        labels.extend(Label(kind=lb.kind, start=lb.start + cursor, end=lb.end + cursor) for lb in sentence.labels)
        cursor += len(sentence.text)

    return Document(text="".join(text_parts), labels=labels, difficulty=resolved_difficulty)


def generate_negative_document(rng: random.Random, template: str | None = None) -> Document:
    """개인정보가 없는(또는 distractor만 있는) 합성 문서 하나를 만든다 — 오탐(FP) 측정용, 정답 라벨은 0개."""
    return _render(template if template is not None else rng.choice(_NEGATIVE_TEMPLATES), rng, "negative")


def templates() -> list[str]:
    return list(_TEMPLATES)


def negative_templates() -> list[str]:
    return list(_NEGATIVE_TEMPLATES)


__all__ = [
    "ALL_KINDS",
    "Document",
    "Label",
    "generate_document",
    "generate_multi_sentence_document",
    "generate_negative_document",
    "negative_templates",
    "templates",
]
