# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이름 탐지기 — 성씨 사전 + 문맥 단서 기반 임시 규칙판(Ollama+Qwen 로컬 LLM 버전 나오기 전까지).

동작 원리:
1. 흔한 한글 성씨(사전) 뒤에 1~2글자 이름이 붙은 자리를 후보로 삼는다.
2. 성씨+이름만으로는 그냥 일반 단어와 구분이 안 되므로("이용", "김치" 등), 앞에 역할어
   ("고객", "환자", "작성자" 등)나 뒤에 존칭("님", "씨" 등)이 붙어 있을 때만 탐지한다 — 둘 다 없으면 버린다.
3. 앞뒤 문맥 단서가 둘 다 있으면 확신도를 높게(0.75), 하나만 있으면 낮게(0.5) 준다.

한계(의도된 트레이드오프): 문맥 단서 단어가 성씨와 무관하게 등장해도 매칭될 수 있어
("고객 이용 안내"의 "이용"이 성씨 "이"+이름 "용"으로 오탐될 수 있음) 정밀도가 다른 규칙
탐지기보다 낮다. 문맥을 실제로 이해하는 로컬 LLM(Ollama+Qwen) 버전으로 교체하기 전까지의
임시 버전임을 감안한다.
"""

from __future__ import annotations

import csv
import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 인구 비중이 높은 한글 성씨. 나머지 200여 개를 다 넣기보다 흔한 것 + 흔한 복성(두 글자)만
# 둔다. 사전 밖 성씨(류·변·탁 등)는 이 규칙으로는 못 잡고, 이름 전용 양식 라벨 뒤에 쌍점·
# 세로줄이 있을 때만 _FORM_NAME_RE가 건진다(#491). 그 밖의 문장에서는 LLM판이 맡는다.
_SURNAMES = [
    # 복성(두 글자) — 정규식에서 긴 것부터 매칭돼야 "선우예진"을 선+우예진이 아닌 선우+예진으로 본다
    "남궁", "선우", "제갈", "황보", "독고", "서문", "사공",
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "남", "심",
    "노", "하", "곽", "성", "차", "주", "우", "구", "민", "나",
    "진", "지", "엄", "채", "원", "천", "방", "공", "현", "함",
]

# 이름 뒤에 자주 오는 직함. 후보 판정 + 규칙 매칭의 suffix 단서로 쓴다(#213).
# 업무·계약 문서는 "홍길동 대표"처럼 직함이 이름과 존칭 사이에 끼어, 존칭만 보던 예전 규칙은
# 이름을 통째로 놓쳤다. 직함 단서 하나만 있으면 확신도 0.5다 — 규칙 전용 경로와 하이브리드
# 안전망(#476부터 확신도 제한 없이 전부 사용) 양쪽에서 잡힌다.
# #394: 기업 임원·전문직·현장 직함을 넓혔다. 실서버로 확인한 흔한 직함(총무·매니저·상무·전무·
# 국장·지점장·간호사·변호사·회계사·코치·감독·강사·인턴·팀원) 옆 이름은 풀네임도 통째로 새고
# 있었다. "부사장"은 "사장"의 부분 문자열로 우연히 잡히던 것을 정식 항목으로 둔다.
_TITLE_CUES = [
    "팀장", "과장", "부장", "차장", "대리", "사원", "실장", "본부장",
    "이사", "대표", "원장", "교수", "주임", "반장", "사장", "회장", "님",
    # 기업·기관 직급
    "총무", "매니저", "상무", "전무", "국장", "처장", "계장", "소장", "지점장", "지사장",
    "부사장", "부원장", "부팀장", "센터장", "사무장", "이사장", "위원장", "위원", "주무관",
    # 전문직·현장 직함
    "간호사", "변호사", "회계사", "세무사", "약사", "의사", "교사", "강사", "상담사",
    # "상담원"(#580): 고객센터 상담 기록에 흔한데 "상담사"만 있어 "담당 상담원 김민수"를 놓쳤다.
    "상담원",
    "연구원", "조교", "기자", "코치", "감독", "인턴", "팀원",
]

# 이름 앞에 오는 역할어 — 뒤에 공백/콜론이 붙어 이름으로 이어진다.
# 서식에서 사람 칸 앞에 붙는 라벨은 이 밖에도 많다 — 환자명·명의자·예금주·서명자·대상자·채용자·
# 지원자·가입자·민원인·학생이 벤치 미탐의 절반 이상이었다(규칙판 FN 127건 중 약 80건).
_PREFIX_CUES = [
    "고객", "환자", "신청자", "작성자", "담당자", "수령인", "수신인", "성명", "이름", "저는",
    "환자명", "고객명", "회원명", "성함", "실명",
    "명의자", "예금주", "입금자", "송금인", "수취인", "발신인", "발송인",
    "서명자", "대상자", "채용자", "지원자", "가입자", "신청인", "청구인", "계약자",
    "피보험자", "보호자", "대리인", "의뢰인", "내담자", "민원인",
    "학생", "응시자", "참석자", "참가자", "면접자", "근로자", "임차인", "임대인",
]

# 이름 뒤에 오는 존칭·역할어 — 공백 없이 붙거나(님께) 공백을 두고(환자분) 이어질 수 있다.
_SUFFIX_CUES = [
    "선생님", "고객님", "환자분",
    "님", "씨", "군", "양",
    "담당자", "작성자", "신청자", "수령인", "수신인",
    "학생", "환자", "회원", "보호자",
]

# 성씨로 시작하지만 실제로는 이 도메인(개인정보 서식)에서 라벨로 흔히 쓰이는 일반 단어 —
# "고객 전화번호", "성명 및 주소" 처럼 역할어 바로 뒤에 붙어 나오면 이름으로 오탐하기 쉽다.
# 이 목록은 **앞부분 일치**(startswith)로 거른다: 뒤에 다른 글자가 이어져도(이사회·이사장·
# 전화번호·이력서) 같은 라벨 계열이라서다. 그래서 여기엔 "그 두 글자로 시작하는 실명이 사실상
# 없는" 단어만 둔다 — "이용"(이용재)·"이유"(이유진)처럼 실명 앞글자와 겹치는 단어는 아래
# _COMMON_WORDS로 옮겼다(startswith로 걸면 실명이 통째로 새어나갔다).
# "이사"는 "대표이사"가 띄어쓰기돼("대표 이사가") 이름으로 오탐되던 걸 막는다(#239).
_NON_NAME_WORDS = (
    "전화번호", "이메일", "주민등록번호", "주민번호", "주민등록증",
    "주소", "나이", "성별", "생년월일", "이사",
    "성명", "성함", "이름", "이력",
)

# 성씨로 시작하는 흔한 2음절 일반명사 — 문맥 단서 옆에 오면 이름처럼 보인다("고객 문의",
# "대표 차량이", "부장 성과가"). 이 목록은 **단어 경계**로 거른다: 뒤가 비한글이거나 단일
# 조사(이·가·은 등)+비한글일 때만 버리고, 다른 글자가 이어지면("정기훈", "이용재", "정보라")
# 실명으로 보고 그대로 잡는다 — 미탐=유출이므로 애매하면 잡는 쪽이다.
# #247의 부서어 5개(구매·정기·홍보·안전·노무)가 여기서 시작됐고, #255가 실측한 잔여 오탐
# (차량·허가·성과·안내)과 서식·업무 문서에서 흔한 것을 더했다. 완전한 목록은 아니다 —
# 긴 꼬리는 LLM판 담당이고, 오탐은 과다 마스킹(안전한 쪽)이라 여기 없는 단어가 새어나가진 않는다.
_COMMON_WORDS = frozenset({
    # 부서·업무어(#247/#255)
    "구매", "정기", "홍보", "안전", "노무", "차량", "허가", "성과", "안내",
    # 서식·문서 라벨
    "이용", "이유", "서류", "서명", "정보", "문의", "문서", "문자", "문제", "양식", "양성",
    "조사", "조건", "조정", "조회", "지원", "지급", "지정", "진행", "신규", "신청",
    "채용", "공지", "공사", "공고", "구성", "구역", "방문", "방침", "배송", "배정",
    "유지", "유통", "임대", "임시", "원본", "원가", "현장", "현황", "하자", "오류",
    "백업", "강의", "강화", "정산", "정책", "장비", "장소", "전달", "전체", "전자", "전화",
    "전송", "주차", "주문", "주간", "민원", "고객", "박스",
    # 흔한 시간·정도 부사(최·이 성씨와 겹친다)
    "최근", "최고", "최종", "최대", "최소", "이전", "이후", "이상", "이내", "이하", "이번",
    "오전", "오후", "한국", "서울",
    # "이름" 단서 뒤에 흔히 오는 일반 명사·부사(#484) — "이름 정밀 탐지"의 "정밀"처럼
    # 서식·기술 문서에서 "이름"이라는 단서 바로 뒤에 자주 등장해 이름으로 오탐됐다.
    "정밀", "문맥", "전혀", "공식",
})

# 직함 전용 단서(존칭 '님' 제외). 이것만으로(다른 단서 없이) 이름을 잡을 땐 성+2자 풀네임을
# 요구한다 — 부서·업무어("구매 부장"의 구매, "대표 이사"의 이사)가 직함과 붙어 이름으로
# 오탐되는 걸 막는다. 존칭(님)은 강한 단서라 이 제약을 걸지 않는다. (앞·뒤 직함 공용)
_TITLE_ONLY_CUES = frozenset(_TITLE_CUES) - frozenset(_SUFFIX_CUES)

# 이름 뒤에 붙는 단일 음절 조사 — 일반명사 뒤에 붙어 단어 경계를 흐리는지 판별에 쓴다(#247).
# "엔"("~에는"의 준말, "이전엔")도 조사로 본다(#484) — 없으면 "이전"(정지어) 뒤에 "엔"이 붙은
# "이전엔"이 조사 경계로 안 잡혀 3글자 이름("이+전+엔")처럼 보여 "이전엔 팀장"이 오탐됐다.
# "랑"·"께"도 흔한 단일 음절 조사다(#484 리뷰 — "김민수랑", "박서준께"가 낱말 경계 확인
# 때문에 놓치고 있었다).
_JOSA_CHARS = frozenset("이가은는을를도만의에로과와엔랑께")

_SURNAME_ALT = "|".join(sorted(_SURNAMES, key=len, reverse=True))
# 이름 앞 단서 = 역할어 + 직함. 직함이 이름 앞에 오는 형태("대표 홍길동")도 잡는다(#239).
_PREFIX_ALT = "|".join(
    sorted(dict.fromkeys(_PREFIX_CUES + sorted(_TITLE_ONLY_CUES)), key=len, reverse=True)
)
# "양"·"군"은 실명 끝 글자로도 흔하면서(#340) 한 글자라 "양쪽"·"양식"·"군것질" 같은 흔한
# 낱말의 첫 글자와 겹친다 — 뒤가 조사 한 글자 이내이거나 낱말 끝일 때만 존칭으로 받는다
# (#484). 나머지 존칭·직함은 여러 글자라 이런 오탐이 없어 기존대로 둔다.
_AMBIGUOUS_SUFFIX_TITLES = frozenset({"양", "군"})
_JOSA_CHARS_STR = "".join(sorted(_JOSA_CHARS))
_SUFFIX_ALT_PLAIN = "|".join(
    sorted(
        dict.fromkeys(c for c in (_SUFFIX_CUES + _TITLE_CUES) if c not in _AMBIGUOUS_SUFFIX_TITLES),
        key=len,
        reverse=True,
    )
)
_AMBIGUOUS_SUFFIX_ALT = "|".join(sorted(_AMBIGUOUS_SUFFIX_TITLES, key=len, reverse=True))
# 이름 뒤 단서 = 존칭·역할어 + 직함. 직함도 규칙 매칭 단서로 편입한다(#213). "님"은 양쪽에
# 있으므로 dict.fromkeys로 중복을 없앤 뒤 긴 것부터 매칭한다.
_SUFFIX_ALT = (
    _SUFFIX_ALT_PLAIN
    + r"|(?:"
    + _AMBIGUOUS_SUFFIX_ALT
    + r")(?=[" + _JOSA_CHARS_STR + r"]?(?![가-힣]))"
)

# 이름의 2번째 글자로 삼키면 안 되는 글자 — 뒤 suffix 그룹이 잡거나 이름 밖으로 남긴다(#147).
# 탐욕적 매칭이 "고객 심진님"의 "심진님"을 통째로 삼켜 gold("심진")와 어긋나던 문제.
# 님·씨: 이름 음절로 거의 안 쓰인다. 입·는·을·를·과·와·에·께: 이름 끝음절로 쓰이지 않는다
# ("예금주는 고혜입니다"의 "입", "고객 김민을"의 "을"). 반면 군·양은 실명 끝음절로 흔해서
# ("김하양"·"박도군") 여기 넣으면 그 글자를 이름에서 떼어내 유출된다(#340) — 미탐=유출이라
# 이름에 포함(더 가리기=안전). "홍길 군"처럼 공백이 있으면 어차피 suffix 그룹이 잡는다.
# 이·가·은·도·의 같은 조사는 이름 글자와 겹쳐(재이·지은·박도·정의) 규칙으로 뺄 수 없어 제외 —
# "환자 신성의"는 "신성의"로 한 글자 더 가려진다(안전). 정확한 경계는 LLM판이 처리.
_NAME_TAIL_STOP = "님씨입는을를과와에께"

# 이름 바로 뒤에 오면 그 뒤에 무슨 글자가 이어지든 이름이 거기서 끝났다고 보는 어미·조사의
# 첫머리(#600). 서술격 조사("김민수예요"·"박서준이에요"·"김민수였습니다"·"김민수라고"),
# 높임("김민수이신가요"), 두 글자 이상 조사 뒤에 조사가 더 붙는 꼴("김민수에게는"·
# "김민수께서는"·"김민수입니다만")이다. 이름 뒤를 보는 조건들(#484·#579)이 허용 어미를 닫힌
# 목록으로만 들고 있어서, 목록에 없는 어미가 붙으면 앞 단서가 있어도 이름을 통째로 놓쳤다.
# 첫머리만 보므로 더 긴 낱말의 앞부분("하이브리드"의 "하이브" 뒤 "리드")은 여기에 걸리지
# 않아 #484의 오탐 방지는 그대로다.
_OPEN_ENDING_STEMS = (
    "입니다", "이에요", "예요", "이었", "였", "이라", "라고", "라는", "라서", "라면", "란",
    "이신", "이세", "이시", "이십", "인데", "인가", "인지", "이야", "이죠", "이지", "이네",
    "이나", "이든", "이면", "에게", "에서", "께서", "한테", "까지", "부터", "처럼", "보다",
    "마저", "조차", "밖에", "뿐",
)
_OPEN_ENDING_ALT = "|".join(sorted(_OPEN_ENDING_STEMS, key=len, reverse=True))
# #600 전까지 이름 뒤로 받던 꼴(닫힌 어미 목록 + 낱말 끝). 흔한 일반명사(_COMMON_WORDS) 뒤에
# 이 꼴이 오면 지금처럼 이름 후보로 둔다 — 거르면 전부터 가리던 "고객 정밀입니다"(일반명사와
# 겹치는 실명)가 샌다. 이 꼴이 아니고 어미 첫머리로만 받는 새 꼴("고객 정보예요"·
# "고객 정보에게는")이면 낱말이 끝난 것으로 보고 거른다(_is_common_word_at).
_PRE600_NAME_END_RE = re.compile(
    r"(?:입니다|이며|이고|에게서|에게|에서|한테|께서|이랑|하고|처럼|부터|까지|보다|으로|로서"
    r"|[" + _JOSA_CHARS_STR + r"]{1,2}(?:님|씨)?)?(?![가-힣])"
)

# 예외: "을"은 목적격 조사지만 실명 끝 글자로도 쓰인다("김가을"). 위 규칙만 두면
# "김가"까지만 가려 "을"이 샌다(#579). "을" 바로 뒤에 존칭·직함(공백 하나까지)이나 조사,
# 어미 첫머리("김가을인데요"·"김가을마저", #600)가 붙으면 목적격 조사일 수 없으니 이름에
# 넣는다. 뒤가 공백·문장부호면("고객 김민을 만났다") 지금처럼 조사로 보고 뺀다. "김민을 대리로"
# 처럼 목적격 "을" 뒤에 직함 낱말이 오면 "을"까지 가려지지만, 한 글자 더 가리는 쪽이라 안전하다.
_EUL_AS_LAST_SYLLABLE = (
    r"을(?=\s?(?:" + _SUFFIX_ALT_PLAIN + r")|[이가은는의에도만로와과랑께]|(?:" + _OPEN_ENDING_ALT + r"))"
)

# 라벨과 이름 사이 구분자. 예전 규칙(쌍점·공백 두 글자, "성명::홍길동"·줄바꿈 하나 포함)을 그대로
# 두고, 가로 공백 세 칸과 앞뒤 공백을 둔 쌍점·세로줄(" : ", 표 칸 " | ")을 더한다(#491).
# 더한 쪽은 줄을 넘지 않는다. 괄호 설명은 여기서 받지 않는다 — 괄호를 통째로 소비하면
# "담당자(김민수 대리)"처럼 괄호 안에 든 이름을 다시 찾지 않아 샌다(#491 독립 검증).
_LABEL_SEP = r"(?:[:\s]{1,2}|[ \t]{1,3}|[ \t]{0,3}[:|][ \t]{0,3})"

# 이름 전용 양식 라벨. 이 라벨 뒤에 쌍점·세로줄이 오면 성씨 사전 밖 이름도 받는다(#491).
# 공백만 있는 문장("이름 표기 규칙")까지 받으면 일반 낱말이 이름으로 잡히므로 쌍점·세로줄을 요구한다.
# "이력서 접수"·"면허 갱신 신청"은 업무 문서 제목형 라벨이다(#537) — bench 실측에서 "라벨:
# 이름, 뒤정보"(뒤에 콤마로 다른 정보가 이어지는) 형태의 미탐 20건 중 8건이 이 두 라벨
# 뒤였다. 이름 음절 수와 무관하게(2·3음절 모두) 라벨 자체가 어휘에 없어 통째로 샜다 —
# "콤마 뒤 경계 판정 실패"가 아니라 순수한 어휘 누락이었다(라벨을 추가하면 그대로 잡힌다).
_FORM_LABELS = (
    "성명", "이름", "성함", "실명", "예금주", "명의자", "환자명", "고객명", "회원명",
    "수취인", "송금인", "입금자", "신청인", "신청자", "보호자", "대표자",
    "이력서 접수", "면허 갱신 신청",
)

# "이름"은 사람 이름 그 자체를 가리키는 범용 메타 단서라 비인명 문맥("이름 정밀 탐지",
# "파일 이름")과 자주 겹친다 — 정지어(_COMMON_WORDS) 필터를 면제하는 "강한 라벨"에서
# 뺀다(#484 리뷰). 나머지 _FORM_LABELS(명의자·예금주·환자명 등, 좁은 양식 라벨)는 그
# 자체로 이미 사람 자리를 가리키는 문맥이 뚜렷해 강한 단서로 인정한다 — "명의자 공식"
# 처럼 라벨 뒤에 흔한 낱말이 와도 실명일 수 있다. "고객"·"담당자"처럼 훨씬 흔하고 범용인
# _PREFIX_CUES 나머지는 여기 포함하지 않는다 — 포함하면 "담당자 최근 변경"·"고객 문의
# 접수" 같은 기존에 걸러야 했던 오탐까지 강한 단서로 승격돼 버린다(#446 회귀 테스트).
_STRONG_LABEL_PREFIXES = frozenset(_FORM_LABELS) - {"이름"}
# 양식 칸에 이름 대신 들어가는 값과 표 머리행에 흔한 열 이름 — 끝의 조사·"입니다"를 뗀 값이
# 이것과 **완전히 같을 때만** 이름으로 보지 않는다. 앞부분 일치로 거르면 "기재민"처럼 이 말로
# 시작하는 실명이 샌다(#491 독립 검증).
_FORM_NOT_NAMES = frozenset({
    # 자리표시 값
    "없음", "미기재", "미상", "본인", "해당없음", "비공개", "생략", "미정", "기재", "공란", "빈칸",
    "상동", "동일", "별첨", "참조", "하단", "상단", "아래", "모름", "익명", "불명", "무기명", "공석",
    # 작성 안내
    "필수", "선택", "확인", "작성", "기입", "입력", "한글", "영문", "자필", "서명", "날인", "직인",
    # 표 머리행의 열 이름
    "설명", "소속", "직위", "직책", "연락처", "부서", "역할", "비고", "상태", "형식", "경로", "기본값",
    "버전", "관계", "은행", "학번", "타입", "번호", "주소", "전화", "날짜", "금액", "수량", "내용",
    "항목", "구분", "법인", "개인", "회사명", "팀명", "부모", "모친", "부친", "배우자", "대리인",
})
# 은·이·가·도는 이름 끝 글자로도 흔해서("기재은", "재이") 떼지 않는다 — 떼면 "기재"가 되어 걸러지고 샌다.
_FORM_VALUE_ENDING_RE = re.compile(r"(?:입니다|이며|이고|님|씨|[는을를의와과])$")

# 표(CSV·TSV·마크다운)의 구분자. 쉼표를 먼저 시도한다 — 마크다운 표에 쉼표가 포함된 값이
# 들어 있어도(드묾) 세로줄이 없으면 쉼표 판정으로 못 넘어가므로 순서가 결과에 영향을 주지
# 않는다(#526). 슬래시는 "이름 / 부서"처럼 사내 명단에서 칸을 나눌 때 쓴다(#581) — 머리행에
# 이름 열 라벨이 칸 하나로 있어야 표로 보므로 날짜(2024/01/01)·"및/또는" 같은 줄은 걸리지 않는다.
_TABLE_SEPS = (",", "\t", "|", "/")

# 표 값 칸에 들어갈 수 있는 이름 모양 — _FORM_NAME_RE의 name 그룹과 같은 글자 제약(2~4자
# 순한글, 님·씨로 시작 금지)이다. 표 칸은 라벨이 따로 없어 성씨 사전 밖 이름도 받는다(#526).
_TABLE_NAME_VALUE_RE = re.compile(r"(?:(?![님씨])[가-힣]){2,4}")

# 머리행 없이 슬래시로 칸을 나눈 명단 한 줄("김민수 / 개발팀 / 010-…", #581). 첫 칸이 3~4자 이름
# 모양이고, 같은 줄 다른 칸에 전화번호(0으로 시작)·이메일·생년월일이 있을 때만 첫 칸을 이름으로
# 본다. 칸은 셋 이상이어야 한다. 줄 앞 목록 기호("- "·"1. ")는 건너뛴다.
# 2글자 첫 칸과 "숫자만 많은 칸"(날짜·시각·대표번호 1588-…)까지 받으면 "정상 / 처리완료 /
# 2024-01-01 10:00"·"강남 / 역삼 / 02-555-1234" 같은 줄이 이름으로 잡혀 오탐이 17줄 중 6줄이었다.
# 그래서 2글자 이름은 이 경로에서 받지 않는다(한계 — 다른 단서가 있으면 기존 규칙이 잡는다).
_SLASH_RECORD_LEAD_RE = re.compile(r"[ \t]*(?:[-*•·]|\d{1,3}[.)])?[ \t]*")
_SLASH_RECORD_MIN_CELLS = 3
_SLASH_RECORD_MIN_NAME_LEN = 3
_SLASH_RECORD_DETAIL_RE = re.compile(r"@|0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}|생년월일|생일")

# 마크다운 구분행("|---|:--:|--:|")의 칸 — 대시·콜론·공백만으로 이뤄진다. 적어도 한 칸은
# 비어 있지 않아야 진짜 구분행이다(전부 빈 칸인 데이터 행과 헷갈리지 않기 위해).
_TABLE_SEPARATOR_CELL_RE = re.compile(r"[-:\s]*")
_FORM_NAME_RE = re.compile(
    # 라벨 앞에 한글이 붙으면 다른 낱말의 일부다("파일이름: 보고서").
    r"(?<![가-힣])(?P<label>" + "|".join(sorted(_FORM_LABELS, key=len, reverse=True)) + r")"
    # 괄호 설명("성명(한글)")·쌍점·세로줄. 가로 공백만 받아 빈 칸 다음 줄의 라벨을 값으로 먹지 않는다.
    r"(?:\([^()\r\n]{1,12}\))?[ \t]{0,3}[:|][ \t]{0,3}"
    r"(?<![가-힣])(?P<name>(?:(?![님씨])[가-힣]){2,4})"
    # 이름 뒤는 낱말 끝이거나 존칭·조사·"입니다"다. 이름 끝 글자가 조사와 같아도("류하은")
    # 먼저 길게 잡아 떼어내지 않는다 — 떼면 그 글자가 샌다. 목록 밖 어미는 첫머리로 받는다(#600).
    r"(?=(?:" + _OPEN_ENDING_ALT + r")|(?:입니다|이며|이고|님|씨|[은는이가을를의와과도])?(?![가-힣]))"
)

_NAME_RE = re.compile(
    # 역할어·직함 뒤에 조사가 붙은 형태("담당자는 홍길동", "예금주는 김민")도 잇는다 —
    # 서식 문장에서 흔한데 조사 하나 때문에 단서를 통째로 잃고 있었다.
    # 라벨 뒤 구분자는 양식에서 흔한 " : "·표 칸 " | "까지 받는다(#491). 구분자를
    # named group으로 잡아두는 이유는 #484 참고 — 콜론·세로줄처럼 명시적인 구분자가
    # 있으면(공백뿐인 경우와 달리) prefix가 좁은 양식 라벨이 아니어도 강한 단서로 본다.
    r"(?:(?P<prefix>" + _PREFIX_ALT + r")(?:은|는|이|가)?(?P<label_sep>" + _LABEL_SEP + r"))?"
    # 성씨는 단어(어절) 시작이어야 한다 — 앞에 한글이 붙어 있으면 단어 중간이라 이름이 아니다(#158).
    # 이게 없으면 "감지되어"의 "지"(성씨 사전)부터 "지되어"가 이름으로 잡히고, 뒤 "양빈도"의 "양"을
    # 존칭으로 삼켜 오탐이 된다. 앞이 공백/문장부호/문두면 통과하므로 정상 이름은 그대로 잡힌다.
    r"(?<![가-힣])"
    # 성씨 + 1글자, 2번째 글자는 이름 끝에 올 수 없는 글자가 아닐 때만 붙인다(#147).
    r"(?P<name>(?:" + _SURNAME_ALT + r")[가-힣]"
    r"(?:(?![" + _NAME_TAIL_STOP + r"])[가-힣]|" + _EUL_AS_LAST_SYLLABLE + r")?)"
    r"(?:\s?(?P<suffix>" + _SUFFIX_ALT + r"))?"
    # suffix가 없으면(뒤 단서를 못 찾았으면) 이름이 낱말 끝에서 끝나야 한다 — 없으면 "하이
    # 브리드"의 "하이브"처럼 더 긴 낱말의 앞부분만 잘라 이름으로 오탐한다(#484). suffix가
    # 있으면(예: "님께"처럼 존칭 뒤에 조사가 더 붙는 경우) 이 조건을 걸지 않는다 — 그 경계는
    # 이미 suffix 매칭 자체가 보장한다. _FORM_NAME_RE와 같은 종결어미·조사 목록을 쓴다.
    # "에게"·"에서"처럼 "에"로 시작하는 두 글자 조사는 단일 글자 조사 목록(_JOSA_CHARS)만으로
    # 못 잡는다 — 처음엔 "에"만 클래스에 있어 "손인은에서"·"김민수에게"의 이름이 새로 놓쳤다.
    # 리뷰(팀장, PR #571)에서 "한테"·"하고"·"처럼"·"부터"·"까지" 등 두 글자 이상 조사도
    # 빠져 있어 "김민수한테"·"이도현하고" 같은 정상 이름을 대거 놓치는 걸 확인했다 —
    # 완전한 목록은 아니지만 실제 지적된 조사를 전부 추가한다.
    # 조사 뒤에 존칭이 더 붙거나("김가을님"의 "을님" — "을"이 _NAME_TAIL_STOP이라 이름이
    # "김가"에서 끊기고 남은 "을님"이 조사+존칭 조합), 조사가 이어지는 경우("김가을이"의
    # "을이")도 있다 — 단일 글자 조사를 1~2개까지 반복하고 그 뒤에 님·씨가 더 붙어도
    # 받는다(리뷰, PR #571 — main도 "김가"까지만 가렸으니 최소한 그만큼은 가린다).
    # 그래도 목록이 닫혀 있어 "예요"·"였"·"라고"·"께서는" 같은 어미가 붙으면 통째로 샜다 —
    # 그런 어미는 첫머리(_OPEN_ENDING_STEMS)만 보고 받는다(#600). 반말 "야"도 낱말 끝일 때 받는다.
    r"(?(suffix)|(?=(?:" + _OPEN_ENDING_ALT + r")|(?:입니다|이며|이고|에게서|에게|에서|한테|께서"
    r"|이랑|하고|처럼|부터|까지|보다|으로|로서|야|[" + _JOSA_CHARS_STR + r"]{1,2}(?:님|씨)?)?"
    r"(?![가-힣])))"
)

# LLM에 보낼지 정하는 후보 판정용: 한글 두 글자가 붙은 자리. 한국어 이름은 두 글자 이상이다.
_HANGUL_PAIR_RE = re.compile(r"[가-힣]{2}")

# 문맥 단서 전체 (역할어 + 존칭 + 직함). LLM 후보 판정(has_name_candidate)에도 쓴다.
_ALL_CUES = tuple(dict.fromkeys(_PREFIX_CUES + _SUFFIX_CUES + _TITLE_CUES))

# 이름 후보가 단서 단어(역할어·직함) 자체와 글자까지 같으면 이름이 아니다(#450).
# 호칭의 첫 글자가 성씨 사전에 있으면("고"객·"원"장·"차"장) "고객님께"가 "성+이름 + 존칭"으로
# 읽혀 호칭이 이름으로 잡혔다. 앞부분 일치가 아니라 완전 일치로만 거른다 — "원장훈"처럼
# 호칭 글자로 시작하는 실명까지 버리면 유출이다.
_CUE_WORDS = frozenset(_ALL_CUES)

# 역할어·직함 + 조사("원장이", "차장은"). 앞 단서 뒤에서 이걸 이름으로 받아 소비하면, 그 직함이
# 뒤 이름의 앞 단서가 되지 못해 뒤 이름이 샌다("담당자 : 차장은 김민수", #491 독립 검증).
_CUE_WITH_JOSA_RE = re.compile(r"(?:" + _PREFIX_ALT + r")(?:은|는|이|가)")


def _is_hangul(ch: str) -> bool:
    """완성형 한글 음절(가~힣)인지 본다. 일반명사(_COMMON_WORDS)의 낱말 경계를 판정할 때 쓴다."""
    return "가" <= ch <= "힣"


def _name_could_end_at(text: str, pos: int) -> bool:
    """text[pos:]가 이름 뒤에 올 수 있는 꼴(전부터 받던 어미 + 낱말 끝, 또는 어미 첫머리)인지.

    일반명사 뒤 한 글자까지가 세 글자 이름일 수 있는지 볼 때 쓴다. "담당자 정보라는"은
    "정보"+"라는"으로도, 실명 "정보라"+"는"으로도 읽힌다. 뒤쪽으로 읽힐 수 있으면 #600 전처럼
    이름 후보로 둔다 — 거르면 "고객 이상란"·"정보라는" 같은 실명이 샌다(#600 차등 검사).
    """
    return bool(_PRE600_NAME_END_RE.match(text, pos)) or text.startswith(_OPEN_ENDING_STEMS, pos)


def _is_common_word_at(text: str, pos: int) -> bool:
    """text[pos:]가 흔한 2음절 일반명사로 **단어가 끝나는지** — 뒤가 비한글(공백·문장부호·끝)이거나
    단일 조사 뒤에 비한글이 올 때, 또는 #600에서 새로 받는 어미 꼴("정보예요"·"정보에게는")이
    올 때만 True. "정기훈"처럼 글자가 더 이어지면 실명일 수 있어 False."""
    if text[pos : pos + 2] not in _COMMON_WORDS:
        return False
    after = text[pos + 2 : pos + 3]
    if not after or not _is_hangul(after):
        return True
    if (
        text.startswith(_OPEN_ENDING_STEMS, pos + 2)
        and not _PRE600_NAME_END_RE.match(text, pos + 2)
        and not _name_could_end_at(text, pos + 3)
    ):
        return True
    if after in _JOSA_CHARS:
        after2 = text[pos + 3 : pos + 4]
        return not after2 or not _is_hangul(after2)
    return False


def _is_label_word_at(text: str, pos: int, *, strong: bool = False) -> bool:
    """text[pos:]가 이름이 아닌 라벨·일반명사로 시작하는지.

    라벨 단어(_NON_NAME_WORDS: 성명·전화번호…)는 **언제나** 버린다 — 서식 라벨이라
    앞뒤에 단서가 붙어도("작성자 성명 님") 이름이 아니다.

    반면 일반명사 정지어(_COMMON_WORDS: 문서·조정·이상…)는 앞뒤 단서가 **둘 다** 있는
    강한 경우(strong)엔 면제한다. 이 목록에는 2음절 실명과 겹치는 말이 있어서(문서·배정·
    신규·양성·유지·이하·조정 — 생성기 이름 공간과 실측 교집합 7건), 그냥 버리면
    "고객 이상 씨"·"신청자 조정 님" 같은 실명을 놓친다 — 미탐은 곧 유출이다.
    단서가 하나뿐인 약한 경우엔 "대표 차량이"처럼 오탐이 더 위험하므로 그대로 버린다.
    """
    if any(text.startswith(word, pos) for word in _NON_NAME_WORDS):
        return True
    return not strong and _is_common_word_at(text, pos)


def has_name_candidate(text: str) -> bool:
    """이 텍스트에 사람 이름이 있을 가능성이 있는지 — LLM에 보낼지 정하는 느슨한 필터.

    한글 두 글자가 붙은 자리가 있거나 인명 단서(역할어·존칭·직함)가 있으면 후보로 본다. 둘 다
    없는 텍스트(숫자·코드·영문)만 걸러 LLM 호출을 아낀다. 놓치면 이름이 안 가려지므로(유출),
    애매하면 후보로 넘긴다.

    예전에는 성씨 사전과 단서로 걸렀다. 그러면 사전 밖 성씨 이름만 있고 단서도 없는 문장
    ("어제 탁예린 왔어")은 --llm이어도 LLM을 부르지 않아 이름이 그대로 남았다(#494). 단서는
    그대로 본다. 한글이 한 글자씩 떨어진 이름과 한 글자 단서만 있는 문장("Name: 홍 길 동 님")은
    두 글자 기준만으로는 걸러져 이름이 남았다(#521). 예전 필터가 후보로 보던 입력은 모두 받는다.
    """
    return _HANGUL_PAIR_RE.search(text) is not None or any(cue in text for cue in _ALL_CUES)


class NameDetector(Detector):
    """성씨+문맥 단서 기반 임시 이름 탐지기 (로컬 LLM 버전 나오기 전까지)."""

    kind = "name"

    def __init__(self, min_confidence: float = 0.0) -> None:
        """min_confidence 이상인 탐지만 돌려준다.

        LLM판과 함께 안전망으로 쓸 때 0.75를 주면 앞뒤 문맥 단서가 **둘 다** 있는
        확실한 것만 남아, 이 탐지기의 약점인 오탐(0.5짜리)을 섞지 않고 보강할 수 있다.
        """
        self.min_confidence = min_confidence

    def detect(self, text: str) -> list[Detection]:
        """성씨와 1~2글자 이름 후보 가운데 앞뒤 문맥 단서가 있는 것만 이름으로 본다.

        finditer 대신 직접 이어 찾는다. 버린 후보(라벨 단어)가 다음 이름의 앞 단서일 수
        있어서, 그 자리부터 다시 찾아야 뒤 이름을 놓치지 않는다. 단서가 앞뒤 둘 다 있으면
        확신도 0.75, 하나면 0.5를 주고, min_confidence보다 낮으면 버린다.
        """
        found: list[Detection] = []
        pos = 0
        # finditer 대신 직접 이어 찾는다: "신청자 성명 김하늘"에서 "성명"이 이름 후보로 잡혀
        # 버려질 때, 그 "성명"이 실제로는 다음 이름의 앞 단서다. finditer는 "신청자 성명"을
        # 통째로 소비하고 지나가 "김하늘"이 단서 없는 이름이 돼 새어나갔다.
        while (m := _NAME_RE.search(text, pos)) is not None:
            name_start = m.start("name")
            prefix = m.group("prefix")
            suffix = m.group("suffix")
            label_sep = m.group("label_sep")
            # 앞뒤 단서가 둘 다 있거나, 앞 단서가 좁은 양식 라벨(명의자·예금주 등, "이름"
            # 류 범용 메타 단서는 제외)이거나, 구분자에 콜론·세로줄처럼 명시적인 표시가
            # 있으면 강한 근거로 본다(#484 리뷰) — "명의자 공식"(라벨 자체가 강함)·"담당자:
            # 문맥"(콜론이 강한 신호)처럼 라벨 뒤에 흔한 낱말(_COMMON_WORDS)이 와도 그
            # 이름인 사람일 수 있어 정지어 필터를 면제한다. 반면 "담당자 최근 변경"처럼
            # 흔한 역할어 뒤에 공백만 있는 경우는 여전히 약한 단서로 남겨 기존 오탐 방지
            # (#446)를 지킨다.
            has_explicit_sep = label_sep is not None and (":" in label_sep or "|" in label_sep)
            strong = (
                (prefix is not None and suffix is not None)
                or prefix in _STRONG_LABEL_PREFIXES
                or (prefix is not None and has_explicit_sep)
            )
            if m.group("name") in _CUE_WORDS or _is_label_word_at(text, name_start, strong=strong):
                # 라벨 단어는 이름이 아니다. 앞 단서를 달고 잡혔다면 그 단어 자리에서 다시 찾아
                # 그 단어가 다음 이름의 단서가 되게 한다. 같은 자리를 또 잡으면(단서 없이) 넘긴다.
                # 뒤 직함을 달고 잡혔다면 그 직함 자리에서 다시 찾는다 — "고객이 대리 김민수에게"는
                # "고객이"(버림)+"대리"로 먼저 읽히는데, "대리"까지 소비하면 김민수의 앞 단서가
                # 사라져 이름이 통째로 샌다(#580). 직함은 후보보다 뒤에 있어 늘 앞으로 나아간다.
                if prefix is not None and name_start > pos:
                    pos = name_start
                elif suffix is not None:
                    pos = m.start("suffix")
                else:
                    pos = m.end()
                continue
            pos = m.end()
            if name_start > m.start() and _CUE_WITH_JOSA_RE.fullmatch(m.group("name")):
                # 직함+조사는 이름이 아니다. 결과에 남기지 않고, 그 직함부터 다시 찾아 뒤 이름의 단서로
                # 쓴다. 예전에는 "더 가리기"로 남겨 "차장은"이 이름으로 보고됐다(#533).
                pos = name_start
                continue

            has_prefix = prefix is not None
            has_suffix = suffix is not None
            if not has_prefix and not has_suffix:
                continue  # 문맥 단서가 하나도 없으면 일반 단어와 구분 못 하므로 버린다

            # 직함 하나만 단서일 땐(앞이든 뒤든) 성+2자 풀네임(3글자)만 인정 — 부서·업무어가
            # 직함에 붙어 이름으로 오탐되는 걸 막는다(#213 뒤 직함, #239 앞 직함).
            # 부서어+조사("정기가")가 3글자로 둔갑하는 우회(#247)는 위 _COMMON_WORDS 경계
            # 판정이 먼저 거른다.
            title_only = (suffix in _TITLE_ONLY_CUES and not has_prefix) or (
                prefix in _TITLE_ONLY_CUES and not has_suffix
            )
            if title_only and len(m.group("name")) < 3:
                continue

            confidence = 0.75 if (has_prefix and has_suffix) else 0.5
            if confidence < self.min_confidence:
                continue
            found.append(
                Detection(
                    kind=self.kind,
                    start=name_start,
                    end=m.end("name"),
                    text=m.group("name"),
                    confidence=confidence,
                    detector=self.__class__.__name__,
                )
            )
        form_extra = self._form_names(text, found)
        table_extra = self._table_names(text, found + form_extra)
        slash_extra = self._slash_record_names(text, found + form_extra + table_extra)
        found.extend(form_extra)
        found.extend(table_extra)
        found.extend(slash_extra)
        return found

    def _form_names(self, text: str, found: list[Detection]) -> list[Detection]:
        """양식 라벨(성명·예금주 등)과 쌍점·세로줄 뒤의 이름을 찾는다(#491).

        성씨 사전 밖 이름("성명: 류서윤")도 받는다. 양식 칸의 값은 이름일 가능성이 높아서, 위 규칙이
        일반명사로 보고 버린 "이하은"·"이상은"도 받고, 위 규칙이 "김가"까지만 잡은 "김가을"은 끝까지
        넓힌다. 위 규칙이 이미 통째로 덮은 구간은 다시 넣지 않는다.
        """
        if self.min_confidence > 0.75:
            return []
        covered = bytearray(len(text))  # 위 규칙이 잡은 글자 — 겹침 확인을 선형으로 한다
        for d in found:
            covered[d.start : d.end] = b"\x01" * (d.end - d.start)
        extra: list[Detection] = []
        pos = 0
        while (m := _FORM_NAME_RE.search(text, pos)) is not None:
            start, end = m.span("name")
            name = m.group("name")
            value = _FORM_VALUE_ENDING_RE.sub("", name)
            if name in _FORM_LABELS or value in _FORM_LABELS or _is_label_word_at(text, start, strong=True):
                # 값 자리에 다른 라벨이 왔다("성명: 예금주: 류서윤") — 그 라벨부터 다시 찾는다
                pos = start
                continue
            pos = end
            # 직함+조사("신청자 : 차장은 …")도 값이 아니다. 뒤 이름은 위 규칙이 직함을 단서로 잡는다(#533)
            if value in _FORM_NOT_NAMES or _CUE_WITH_JOSA_RE.fullmatch(name) or all(covered[start:end]):
                continue
            extra.append(
                Detection(
                    kind=self.kind,
                    start=start,
                    end=end,
                    text=name,
                    confidence=0.75,
                    detector=self.__class__.__name__,
                )
            )
        return extra

    def _table_names(self, text: str, found: list[Detection]) -> list[Detection]:
        """표(CSV·TSV·마크다운) 머리행에 이름 열 라벨이 있으면 아래 행의 같은 열 값을 찾는다(#526).

        같은 줄 라벨(`_form_names`)은 라벨과 값이 한 줄에 있을 때만 본다 — 고객 명단처럼
        머리행에 열 이름만 있고 값은 아래 행에 나열되는 표는 놓친다. 한 줄씩만 훑어 선형
        시간을 유지한다(수만 행 CSV도 문서 길이에 비례).
        """
        if self.min_confidence > 0.75:
            return []
        covered = bytearray(len(text))
        for d in found:
            covered[d.start : d.end] = b"\x01" * (d.end - d.start)

        extra: list[Detection] = []
        lines = text.splitlines(keepends=True)
        offset = 0
        i = 0
        n_lines = len(lines)
        while i < n_lines:
            line = lines[i]
            header = self._table_header(line.rstrip("\r\n"))
            if header is None:
                offset += len(line)
                i += 1
                continue

            sep, name_col, n_cols = header
            offset += len(line)
            i += 1
            while i < n_lines:
                row = lines[i]
                row_text = row.rstrip("\r\n")
                if row_text.strip() == "":
                    break  # 빈 줄 — 표가 끝났다
                cells = self._table_cells(row_text, sep)
                if cells is None or len(cells) != n_cols:
                    break  # 칸 수가 달라졌거나(#526) 따옴표가 안 닫혔다 — 표가 끝났다
                if self._is_table_separator_row(cells):
                    offset += len(row)
                    i += 1
                    continue  # 마크다운 구분행("|---|")은 건너뛰고 계속한다
                value, v_start, v_end = cells[name_col]
                start, end = offset + v_start, offset + v_end
                if self._looks_like_table_name(value) and not all(covered[start:end]):
                    extra.append(
                        Detection(
                            kind=self.kind,
                            start=start,
                            end=end,
                            text=value,
                            confidence=0.75,
                            detector=self.__class__.__name__,
                        )
                    )
                offset += len(row)
                i += 1
        return extra

    def _slash_record_names(self, text: str, found: list[Detection]) -> list[Detection]:
        """머리행 없이 슬래시로 칸을 나눈 명단 줄의 첫 칸 이름을 찾는다(#581).

        "김민수 / 개발팀 / 010-3456-7890"처럼 같은 줄의 전화번호는 가려지고 이름만 남던
        경우다. 오탐을 줄이려고 조건을 좁게 건다 — 칸이 셋 이상, 첫 칸이 성씨로 시작하는
        3~4자 한글이고 흔한 낱말·열 이름이 아니며, 다른 칸에 전화번호·이메일·생년월일이 있다.
        확신도는 단서 하나짜리와 같은 0.5다. 한 줄씩만 훑어 선형 시간을 유지한다.
        """
        if self.min_confidence > 0.5:
            return []
        covered = bytearray(len(text))
        for d in found:
            covered[d.start : d.end] = b"\x01" * (d.end - d.start)

        extra: list[Detection] = []
        offset = 0
        for line in text.splitlines(keepends=True):
            body = line.rstrip("\r\n")
            if body.count("/") >= _SLASH_RECORD_MIN_CELLS - 1:
                cells = body.split("/")
                lead = _SLASH_RECORD_LEAD_RE.match(cells[0]).end()
                value = cells[0][lead:].rstrip()
                start = offset + lead
                end = start + len(value)
                if (
                    self._looks_like_slash_record_name(value)
                    and any(self._looks_like_record_detail(cell) for cell in cells[1:])
                    and not all(covered[start:end])
                ):
                    extra.append(
                        Detection(
                            kind=self.kind,
                            start=start,
                            end=end,
                            text=value,
                            confidence=0.5,
                            detector=self.__class__.__name__,
                        )
                    )
            offset += len(line)
        return extra

    @staticmethod
    def _looks_like_slash_record_name(value: str) -> bool:
        """슬래시 명단 첫 칸이 이름으로 볼 만한지 — 표 값 기준에 성씨 시작과 흔한 낱말 거르기를 더한다.

        표와 달리 머리행이 이름 열이라고 알려 주지 않으므로, 성씨로 시작해야 하고 "서울"·"정기"
        같은 흔한 낱말(_COMMON_WORDS)도 버린다.
        """
        return (
            len(value) >= _SLASH_RECORD_MIN_NAME_LEN
            and NameDetector._looks_like_table_name(value)
            and value.startswith(tuple(_SURNAMES))
            and value not in _CUE_WORDS
            and not _is_common_word_at(value, 0)
        )

    @staticmethod
    def _looks_like_record_detail(cell: str) -> bool:
        """사람 기록임을 보여 주는 칸인지 — 0으로 시작하는 전화번호, 이메일("@"), 생년월일·생일."""
        return _SLASH_RECORD_DETAIL_RE.search(cell) is not None

    @staticmethod
    def _table_header(line: str) -> tuple[str, int, int] | None:
        """이 줄이 표 머리행이면 (구분자, 이름 열 인덱스, 전체 칸 수)를 돌려준다."""
        for sep in _TABLE_SEPS:
            if sep not in line:
                continue
            cells = NameDetector._table_cells(line, sep)
            if cells is None or len(cells) < 2:
                continue
            for idx, (value, _start, _end) in enumerate(cells):
                if value in _FORM_LABELS:
                    return sep, idx, len(cells)
        return None

    @staticmethod
    def _table_cells(line: str, sep: str) -> list[tuple[str, int, int]] | None:
        """구분자로 줄을 셀로 나눠 (표시할 값, 줄 안에서의 시작, 끝) 목록을 돌려준다.

        `csv` 표준 모듈로 나눈다 — 쉼표 구분 칸이 따옴표로 통째로 감싸여 있으면("김민수",
        "인사팀, 신규") 안쪽에 구분자가 있어도 한 칸으로 보고 따옴표를 벗긴 값을 쓴다(#526).
        파싱할 수 없는 줄(따옴표가 안 닫힘 등)은 None을 돌려준다. 값의 원래 위치는 줄에서
        순서대로 찾아나간다 — 실제 이름 값에는 따옴표 이스케이프(`""`)가 거의 없어 안전하다.
        """
        try:
            raw_values = next(csv.reader([line], delimiter=sep), [])
        except csv.Error:
            return None
        cells: list[tuple[str, int, int]] = []
        pos = 0
        for raw in raw_values:
            value = raw.strip()
            idx = line.find(value, pos)
            if idx == -1:
                idx = pos
            cells.append((value, idx, idx + len(value)))
            pos = idx + len(value)
        return cells

    @staticmethod
    def _is_table_separator_row(cells: list[tuple[str, int, int]]) -> bool:
        """마크다운 구분행("|---|:--:|--:|")인지 — 모든 칸이 대시·콜론·공백뿐이고, 적어도
        한 칸은 비어 있지 않을 때만 그렇다(전부 빈 칸인 데이터 행과 구분하기 위해)."""
        has_content = False
        for value, _start, _end in cells:
            if not _TABLE_SEPARATOR_CELL_RE.fullmatch(value):
                return False
            if value:
                has_content = True
        return has_content

    @staticmethod
    def _looks_like_table_name(value: str) -> bool:
        """표 값 칸의 문자열이 이름으로 볼 만한지 — 양식 칸(_form_names)과 같은 기준이다."""
        if not _TABLE_NAME_VALUE_RE.fullmatch(value):
            return False
        if value in _FORM_LABELS or value in _FORM_NOT_NAMES:
            return False
        if _CUE_WITH_JOSA_RE.fullmatch(value):
            return False
        return not _is_label_word_at(value, 0, strong=True)
