# bench — 합성 벤치마크

**담당: seoyeon ([@seoyeon056](https://github.com/seoyeon056))** · 상태: ✅ 시작 가능 (스켈레톤 머지 완료)

저작권·개인정보 걱정 없는 **자체 합성 평가 데이터셋**과 정확도(F1) 측정 스크립트. 공개 벤치마크는 이 프로젝트의 핵심 차별화 포인트다.

## 규칙 (실격 사유와 직결 — 예외 없음)

- **진짜 개인정보 절대 금지** — 모든 이름·번호·주소는 생성기로 만든 합성 데이터
- **AI Hub 등 외부 데이터셋 원본 커밋 금지**(재배포 제한) — 로컬 참고용으로만 사용

## 구성

```
generator/
  entities.py     # 종류별 합성 값 생성 (name/phone/email/rrn/address/card/biz_reg/passport/account)
  distractors.py  # 개인정보가 아닌 '헷갈리는' 값 생성 (오탐 측정용)
  documents.py    # 문장 템플릿에 값을 심어 문서 + 라벨(span) 생성
generate_dataset.py  # CLI — JSONL 데이터셋 생성
evaluators/           # 평가 도구 모음 — "무엇을 평가하는가"별로 파일 하나
  evaluate.py            # CLI — core Pipeline.scan() 결과 vs 정답 → precision/recall/F1 리포트 (종류별+난이도별)
  mask_quality.py        # 마스킹 결과물 자체의 개인정보 유출(완전/부분) 여부 검증 로직
  evaluate_masking.py    # CLI — 마스킹 결과에 개인정보가 실제로 남아있는지(유출률) 평가 (--strategy로 mask/label/pseudonym 선택)
  confidence_analysis.py # CLI — confidence 임계값별 precision/recall/F1 변화 분석
  compare_name_detectors.py  # CLI — 이름 탐지 규칙판 vs 하이브리드(LLM) 정확도 비교
datasets/            # 생성된 평가셋 (정답 라벨 포함)
reports/             # evaluate.py --report로 저장한 마크다운 리포트 (결과보고서 첨부용)
tests/               # 생성기·평가 로직 단위 테스트
```

## 사용법

```bash
# 1. 데이터셋 생성 (재현 가능하도록 seed 고정, 기본 25%는 오탐 측정용 무-개인정보 문서)
python -m bench.generate_dataset --count 500 --seed 42 --out bench/datasets/synth_v1.jsonl

# 2. core 탐지기 정확도 평가 (--report로 마크다운 리포트 파일도 저장)
python -m bench.evaluators.evaluate bench/datasets/synth_v1.jsonl --report bench/reports/report_v1.md
```

500건 기준 최신 실측(#255 재측정, seed=42):

| kind | precision | recall | f1 | 비고 |
|---|---|---|---|---|
| email / biz_reg / card | 1.000 | 1.000 | 1.000 | 변동 없음 |
| phone | 1.000 | 1.000 | 1.000 | 050X 평생번호·안심번호 포함 유지 |
| rrn | 1.000 | 1.000 | 1.000 | 점(.) 구분자 포함 유지 — 아래 confidence 절 참고 |
| account | 1.000 | 1.000 | 1.000 | 문맥어 하드 게이트라 confidence가 항상 정확히 0.6으로 고정 — 아래 confidence 절 참고 |
| passport | 1.000 | 1.000 | 1.000 | 변동 없음 |
| address | 1.000 | 1.000 | 1.000 | core [#252](https://github.com/ChoHyeonChan/maskingtape/pull/252)가 [#248](https://github.com/ChoHyeonChan/maskingtape/issues/248)(계사 어미 미탐)을 고쳐 recall 1.000 완전 복구 — 재현 코드로 직접 재확인. 아래 참고 |
| name | 0.832 | 0.679 | 0.748 | core #252가 [#247](https://github.com/ChoHyeonChan/maskingtape/issues/247)(조사 삼킴으로 3글자 가드 우회)을 **부분적으로만** 고쳤다 — 하드코딩 5개 부서어만 막고 그 밖은 여전히 뚫림. 잔여 위험을 negative 데이터로 처음 실측했더니 precision이 오히려 더 떨어짐(0.937→0.832, FP 16건→47건, 이 중 33건이 negative-difficulty 문서). [#255](https://github.com/ChoHyeonChan/maskingtape/issues/255)로 남김, 아래 참고 |

card는 `gen_account_number_like`가 구분자 없이 13자리 이상을 만들 때 core `CreditCardDetector`의
"구분자 없는 13~19자리" 분기와 우연히 겹칠 수 있다는 걸 이번 재측정 중 실제로 재현했다
(`"주문번호 7957621463516"`이 card로 오탐, Luhn 우연 통과). `gen_account`가 이미 갖고 있던
Luhn 무효화 가드(#180)를 `gen_account_number_like`에도 똑같이 적용해 해결하고, 500회 반복
회귀 테스트(`test_account_number_like_distractor_is_never_detected_as_card`)를 추가했다 —
같은 대회 데이터셋을 재생성할 때마다 이런 우연한 형식 충돌이 새로 드러날 수 있다는 걸 다시
확인한 사례다.

address·card는 한때 이 표에서 문제(F1 0.371, 오탐 2건)가 있었는데, core 쪽에서 이미 수정됐다
(각각 [#86](https://github.com/ChoHyeonChan/maskingtape/issues/86), [#87](https://github.com/ChoHyeonChan/maskingtape/issues/87)로
발견해 확인 후 중복 종료 — 실제 수정은 조현찬님이 #69/#86 관련 커밋에서 먼저 완료해둔 상태였음).
card는 `gen_card`(Visa/Mastercard/Amex 계열 IIN + Luhn 체크섬)로 데이터셋에 정답 라벨이 생기면서
처음으로 실측이 가능해졌다 — `#69`(distractor가 카드로 오탐되던 문제)의 회귀 방지 테스트
(`test_distractors_are_never_detected_as_card`)도 같이 추가했다.

`biz_reg`(사업자등록번호)는 core에 `BusinessRegistrationDetector`가 새로 추가되면서([#120](https://github.com/ChoHyeonChan/maskingtape/issues/120)/[#121](https://github.com/ChoHyeonChan/maskingtape/pull/121))
생긴 kind다. `#123`에서 두 가지를 발견해 고쳤다: ① bench에 `biz_reg` 정답 라벨이 아예 없어
이 탐지기의 정확도가 전혀 측정되지 않던 사각지대 — `gen_biz_reg`(국세청 체크섬 검증 알고리즘을
거꾸로 풀어 항상 유효한 값을 생성, `gen_card`의 Luhn 방식과 동일한 패턴)와 계약서·세금계산서
템플릿을 추가해 해결. ② 기존 `gen_business_reg_number` distractor가 체크섬 없이 완전 난수라
~10% 확률로 우연히 유효한 체크섬이 나와 오탐될 수 있던 문제(500건 재현에서 실제로 1건 발생을
확인) — 유효 체크 숫자를 계산한 뒤 일부러 다른 숫자로 바꿔 항상 무효가 되도록 고쳤다.

`passport`(여권번호)도 같은 패턴 — core에 `PassportDetector`가 추가돼 `default_detectors()`에
이미 들어가 있었는데 bench가 못 따라가서 정확도가 전혀 측정되지 않고 있었다(#139). 이 탐지기는
**체크섬이 없다**(구여권 `M12345678`, 신여권 `M123A4567` 형식 + "여권" 문맥어 유무로만 확신도를
0.6/0.9로 가른다) — 그래서 `gen_biz_reg`처럼 "체크섬을 무효화"하는 방법 자체가 없고, 오탐 여부는
오직 형식이 우연히 겹치는지에 달려 있다. 500건 재현에서는 오탐이 없었지만, 기존 distractor
전체 풀에 대해 300회 반복 회귀 테스트(`test_distractors_are_never_detected_as_passport`)를 추가해
앞으로도 우연히 겹치지 않는지 계속 확인한다.

다른 kind들(`phone`/`rrn`/`biz_reg`)은 형식은 비슷하지만 실제로는 아닌 값을 **일부러 만드는**
전용 distractor가 있는데(`gen_invalid_phone_like`·`gen_invalid_rrn_like`·`gen_business_reg_number`),
`passport`만 그런 전용 distractor가 없어 "기존 풀이 우연히 안 겹치는지" 소극적으로만 확인하고
있었다(#145). `gen_passport_like_code`를 추가해 사원번호·상품 시리얼·로트번호처럼 실제 업무에
흔한 "M/S/R/O/D + 숫자" 코드를 만들되, core 정규식이 요구하는 정확한 자릿수(8자리, 또는
3자리+문자+4자리)에서 하나 벗어나게(7·9자리) 해서 체크섬 없는 kind에서도 명시적인 근접 미스
방어를 갖췄다.

`account`(계좌번호)는 core에 `AccountDetector`가 새로 추가되면서([#176](https://github.com/ChoHyeonChan/maskingtape/pull/177))
생긴 kind다(#180). 다른 체크섬 없는 kind(`passport`)와도 다른 독특한 설계다 — 문맥어("계좌",
"입금", "은행", "뱅크" 등)가 매치 앞뒤 15자 안에 없으면 **confidence를 낮추는 게 아니라 아예
탐지를 안 한다**(하드 게이트). `gen_account`로 은행별 그룹 자릿수 다양성(2~4그룹, 그룹당
2~7자리)을 만들고, 모든 positive 템플릿에 문맥어를 반드시 포함시켰다. distractor
쪽은 `gen_account_number_like`(형식은 같지만 문맥어 없는 문장에만 심는다)로 하드 게이트가
실제로 오탐 없이 작동하는지 확인한다. 구분자 없이 붙여 쓴 13~14자리 표기는 core
`CreditCardDetector`의 "구분자 없는 13~19자리" 분기와 형식이 겹칠 수 있어(Luhn까지 우연히
통과하면 card로도 잡혀 겹침 병합이 얽힘 — `gen_business_reg_number`가 겪은 것과 같은 종류의
우연) `gen_account`가 생성 시점에 직접 Luhn을 확인해 우연히 통과하면 마지막 자리를 일부러
바꿔 항상 무효로 만든다.

`address`(주소)는 지금까지 지번·도로명·시/도 없는 시/군 표기까지 늘 동/번지(또는 도로명)를
포함한 "완전한" 주소만 만들었다(#195). `gen_address`에 12% 확률로 시/도만(confidence 0.5)
또는 시/도+구만(confidence 0.65) 생성하는 분기를 추가해 이 구간을 처음 실측했는데, 그 과정에서
**시/도명 뒤에 조사가 공백 없이 붙으면("서울특별시에") core가 아예 못 잡는** 진짜 core 버그를
찾아 [#196](https://github.com/ChoHyeonChan/maskingtape/issues/196)으로 남겼다(당시 address
recall이 1.000→0.968로 떨어짐, FN 3건).

**이번(#223) 재측정에서 #196이 머지된 걸 확인했다** — core가 시/도명 뒤 조사(에/로/의/은/는
등)를 화이트리스트로 허용하도록 `_ADDR_RE`를 고쳤다. 재현 코드를 다시 돌려 실제로 해결됐는지
직접 확인했다:

```python
d.detect("본사는 서울특별시에 위치하며...")  # -> [('서울특별시', 0.5)]  이제 정상 탐지
```

address recall이 1.000으로 복구됐다(FN 0건). confidence 분포 자체(0.5~1.0)는 그대로 남아있어
임계값 위험은 여전히 유효하다 — 아래 confidence 절 참고.

**하지만 #196의 조사 화이트리스트는 완전하지 않았다** — 500건 재측정(#246) 중 기존 템플릿
("자택 주소는 {address}입니다.")이 부분 주소와 우연히 만나 다시 FN 1건이 재현됐다. 원인을
추적해보니 이번엔 진짜 "조사"가 아니라 **"이다"의 활용형(계사 어미)**이었다:

```python
d.detect("자택 주소는 광주광역시입니다.")   # -> [] 미탐지 (계사 어미는 화이트리스트에 없음)
d.detect("자택 주소는 광주광역시예요.")     # -> [] 미탐지
d.detect("자택 주소는 광주광역시에 있습니다.")  # -> 정상 (조사 "에"는 화이트리스트에 있음)
```

"주소는 X입니다"는 자기 주소를 설명하는 매우 흔한 표현인데도 여전히 놓쳐서
[#248](https://github.com/ChoHyeonChan/maskingtape/issues/248)로 core에 남겼는데, core
[#252](https://github.com/ChoHyeonChan/maskingtape/pull/252)가 `_JOSA` 화이트리스트에
"입니다"/"입니까"/"예요"/"였"을 추가해 고쳤다. 재현 코드를 다시 돌려 실제로 해결됐는지
직접 확인했다:

```python
d.detect("자택 주소는 광주광역시입니다.")  # -> [('광주광역시', 0.5)]  이제 정상 탐지
d.detect("자택 주소는 광주광역시예요.")    # -> [('광주광역시', 0.5)]  정상
d.detect("서울특별시청에서 회의했습니다.")  # -> []  계사 아닌 "청"은 여전히 정상 제외(#196)
```

address recall이 1.000으로 완전히 복구됐다 — 회귀 테스트도 새 동작을 지키도록 갱신했다.

`rrn`(주민등록번호)에 **점(.) 구분자**(`800101.1234560`)가 새로 추가됐다(#209/#223) — core
`RRNDetector`가 오늘 이 표기를 지원하게 됐는데, bench의 구분자 목록(`_RRN_SEPARATORS_MIXED`/`_HARD`)이
줄곧 하이픈·공백·붙임만 두고 점은 core가 아직 안 잡던 시절 그대로 빼놓고 있었다. 목록에 `.`을
추가하는 한 줄로 반영했다.

`phone`(전화번호)에 **050X 평생번호·안심번호**(`0507-1234-5678`, `050-1234-5678`)가 새로
추가됐다(#211/#223) — 실번호를 숨기려 쓰는 개인 연락처라 그 자체가 개인정보다. core
`PhoneDetector`의 유선 분기(`50\d?`)와 같은 confidence tier로 잡히므로 `gen_phone`에 새 변형
하나만 추가하면 됐다.

`name`(이름)에는 **역할어·존칭 없이 직함만 있는 문맥**("홍길동 대표가 서명했다")이 새로
추가됐다(#213/#223) — core `NameDetector`가 `_TITLE_CUES`(팀장/대표/이사 등)를 오늘부터 suffix
단서로도 쓰게 됐다. 다만 core는 이 단서 하나만으론 **성+2음절 이상 풀네임(3글자 이상)만**
인정한다 — "구매 부장"처럼 부서·업무어가 성씨와 우연히 겹쳐 오탐되는 걸 막는 설계다. 직접
재현해 이 가드가 실제로 지켜지는지 확인했다:

```python
NameDetector().detect("홍길동 대표가 서명했다.")        # -> [('홍길동', 0.5)]  3글자, 정상 탐지
NameDetector().detect("김민 부장이 결재했습니다.")        # -> []  2글자, 설계상 미탐
NameDetector().detect("구매 부장이 결재했습니다.")        # -> []  부서어 오탐 가드 정상 동작
```

이 트레이드오프를 그대로 반영해 positive 템플릿 4개(직함-only)와 negative 템플릿 3개(부서어
오탐 가드 검증, core 이슈 예시 그대로 사용)를 추가했다 — 그 결과 name recall이 의도적으로
더 낮아졌다(0.691→0.661, FN 16건은 전부 이 설계된 한계). 회귀 테스트로 "3글자는 잡히고 2글자는
안 잡히고 부서어는 절대 안 잡힌다"는 계약 셋을 모두 고정해뒀다.

**직함이 이름 앞에 오는 형태도 추가됐다**([#239](https://github.com/ChoHyeonChan/maskingtape/issues/239)/[#246](https://github.com/ChoHyeonChan/maskingtape/issues/246))
— "대표 홍길동", "부장 김철수"처럼 직함이 이름 **뒤**가 아니라 **앞**에 오는 형태다(#213과
대칭인 사각지대). "대표이사"가 띄어써지면("대표 이사가") "이사"가 성씨 "이"+"사"로 오탐되던
것도 core가 `_NON_NAME_WORDS`에 "이사"를 추가해 막았다. positive 템플릿 3개(직함-앞)와
negative 템플릿 2개("대표 이사가"/"대표 이사회에서")를 대칭으로 추가했다.

**그런데 그때 진짜 새 버그를 발견했다** — [#247](https://github.com/ChoHyeonChan/maskingtape/issues/247).
#239의 "성+2음절 이상 풀네임만 인정" 가드는 2음절 후보 바로 뒤에 조사가 공백 없이 붙으면
(정상적인 한국어 주어 표기) 뚫린다. `_NAME_RE`의 선택적 2번째 글자는 님/씨/군/양 4글자만
제외해서, 조사("이"/"가")도 그대로 삼켜 "3글자"로 둔갑시키기 때문이다("정기가"=정기+가).

**core [#252](https://github.com/ChoHyeonChan/maskingtape/pull/252)가 고쳤지만, 완전히는
아니다.** 하드코딩된 5개 stem(`_DEPT_STEMS = {"구매", "정기", "홍보", "안전", "노무"}`)만
조사-삼킴 우회를 막는 방식이라 커밋 메시지에도 "완전한 목록은 아니고(긴 꼬리는 LLM 담당)"라고
명시돼 있다. 직접 확인해보니 목록 밖의 흔한 업무어는 여전히 그대로 뚫린다:

```python
NameDetector().detect("대표 정기가 참석했습니다.")   # -> []  목록에 있음, 정상 차단
NameDetector().detect("대표 차량이 배정되었습니다.")  # -> [('차량이', 0.5)]  목록 밖, 오탐
NameDetector().detect("대표 허가가 필요합니다.")     # -> [('허가가', 0.5)]  오탐
```

"차량"·"허가"·"성과"·"안내" 전부 실제 인명이 아닌 흔한 업무 용어이고, 성씨 사전과 우연히
겹치는(차/허/성/안 전부 성씨) 2음절 단어라는 점에서 원래 #213/#239가 막으려던 것과 정확히
같은 유형이다. 이 4개를 negative 템플릿으로 추가해 500건 재측정으로 잔여 위험을 처음
정량화했더니 — **negative-difficulty 문서 중 33건에서 오탐이 발생했다**(negative 문서
약 125건 중 26% — 이 4개 템플릿이 뽑힐 때마다 사실상 매번 재현됨). [#255](https://github.com/ChoHyeonChan/maskingtape/issues/255)로
남겼다 — 다만 core가 "긴 꼬리는 LLM 담당"이라고 이미 방향을 밝혀둔 걸 보면 의도된 부분
해결일 수 있어, 이 이슈는 "완전 미해결 버그"보다는 "알려진 한계의 정량화" 성격이 강하다.
회귀 테스트로 현재 동작(5개는 차단, 나머지는 통과)을 고정해뒀다.

**참고로 이 오탐은 "유출"은 아니다** — negative 문서에는 애초에 가릴 개인정보가 없으므로,
"차량이"를 잘못 이름으로 표시해 마스킹해도 실제로 새는 정보는 없다(과다 마스킹, 안전한
방향의 실패). precision을 깎아 사용자 신뢰를 떨어뜨리는 문제이지, CONTRIBUTING이 최우선으로
보는 "탐지 실패=유출" 문제는 아니다 — 아래 마스킹 품질 절에서도 이 구분이 그대로 확인된다.

## 오탐(False Positive) 측정

기존에는 데이터셋 전체가 "개인정보가 있는 문서"뿐이라 재현율(recall)만 측정 가능했고,
core가 개인정보 아닌 걸 잘못 잡아내는지(정밀도, precision)는 검증 불가능했다.

`generator/distractors.py`가 주문번호·사업자등록번호·날짜·가격처럼 숫자가 섞여 있지만
개인정보는 아닌 값과, 지역번호·생년월일이 실제로는 존재하지 않는 '전화번호/주민번호 모양',
사원번호·상품 코드처럼 자릿수만 다른 '여권번호 모양' 값을 만든다. `--negative-ratio`(기본
0.25)만큼의 문서는 정답 라벨이 0개인 채로 생성되고, core가 여기서 뭔가를 탐지하면
`evaluate.py`가 그대로 FP로 집계한다.

## ReDoS 방지 회귀 테스트

core detector 여러 개가 "정규식 반복에 상한을 둬 ReDoS(정규식 과다 역추적)를 막는다"를
docstring/주석에 명시하고 있다(`email.py`는 상한이 없던 시절 40만 자·`@` 없음 입력에서
1.4초 걸렸던 실측 사례까지 남겨뒀다). 하지만 이 속성을 지키는지 확인하는 자동 테스트가
없어서, 누군가 나중에 정규식을 느슨하게 고치면 이 회귀를 아무도 못 잡는 사각지대였다([#162](https://github.com/ChoHyeonChan/maskingtape/issues/162)).

`tests/test_detector_redos.py`가 core의 9개 규칙판 detector 전부(#180에서 추가된
`account` 포함)에 구분자 없이 이어진 40만 자 적대적 입력을 넣고, 시간 예산(5초, 여유
있게 잡음) 안에 끝나는지 확인한다 — 직접 측정해보면 현재는 전부 0.15초 이내로 통과하지만,
이 테스트가 없으면 앞으로 그렇다는 보장이 없다.

## 문장·표기 다양성

실제 문서는 같은 개인정보라도 표기 형식이 제각각이라, 생성기도 그 다양성을 반영한다:

- **전화번호**: 하이픈(`010-1234-5678`)뿐 아니라 점(`.`)·공백·구분자 없음(`01012345678`)·
  `+82` 국제표기까지 core가 허용하는 형식을 무작위로 섞는다. **휴대폰뿐 아니라 유선전화**
  (`02-1234-5678`, `031-123-4567` 등 core `PhoneDetector`가 지원하는 지역번호 전체)도 생성한다 —
  이전엔 휴대폰만 만들어서 유선전화 경로가 한 번도 실측된 적이 없었다. **050X 평생번호·안심번호**
  (`0507-1234-5678`, `050-1234-5678`)도 섞는다([#211](https://github.com/ChoHyeonChan/maskingtape/issues/211)).
- **이메일**: 기본 표기에 더해 **plus 표기**(`user+tag@example.com`)와 **서브도메인**
  (`user@mail.example.com`)도 섞는다 — core `EmailDetector`의 로컬 파트 문자 집합(`+` 포함)과
  다중 도메인 라벨 지원을 실제로 검증한다.
- **주민번호**: 하이픈/공백/점(`.`)/구분자 없음([#209](https://github.com/ChoHyeonChan/maskingtape/issues/209)),
  1900·2000년대 성별코드를 모두 커버. **외국인등록번호**
  (성별코드 5~8)도 15% 확률로 섞는다([#148](https://github.com/ChoHyeonChan/maskingtape/issues/148)) —
  core `RRNDetector`의 `_CENTURY` 매핑이 이미 5~8을 내국인과 동일한 정규식·체크섬으로 처리하는데
  bench가 1~4만 만들어서 한 번도 실측된 적이 없었다. **체크섬 없는(2020-10 이후 발급분) 케이스**도
  15% 확률로 섞는다([#159](https://github.com/ChoHyeonChan/maskingtape/issues/159)) — core는 생년월일만
  유효하면 체크섬이 틀려도 confidence 0.85로 여전히 탐지하는데, bench가 지금까지 항상 유효한
  체크섬만 만들어서 이 경로가 한 번도 실측된 적이 없었다. confidence 임계값을 0.9 이상으로
  올리면 이 케이스가 통째로 걸러진다는 걸 처음으로 데이터로 확인했다 — 아래 confidence 절 참고
- **주소**: 지번 주소(`강남구 역삼동 12-3`)와 도로명 주소(`테헤란로12길 3`, 아파트 동/호 포함)에 더해,
  **시/도 없이 시/군으로 시작하는 표기**(`성남시 분당구 정자동 45-6`, `김포시 사우동 12-3`,
  `양평군 양서면 8-7`)도 `hard`/`mixed` 난이도에서 섞는다([#118](https://github.com/ChoHyeonChan/maskingtape/issues/118)) —
  core의 `_ADDR_NO_PROVINCE_RE` 게이트(시/군 바로 뒤에 구·동/읍/면/리가 와야 함)를 만족하는
  조합만 쓴다. 조사 '로'가 붙거나(`성남시로`) 구가 단독으로 오는(`강남구에서`) 지역 언급은
  distractor(`gen_region_mention_like`)로 별도 추가해 오탐 여부를 검증한다. **부분 주소**(시/도만·
  시/도+구만, 동/번지 없음)도 12% 확률로 섞는다([#195](https://github.com/ChoHyeonChan/maskingtape/issues/195)) —
  명함·채용공고처럼 실제로 흔하지만, 기존 스타일은 전부 동/번지를 포함해 confidence 0.4~0.7
  구간이 한 번도 실측된 적이 없었다(당시 시/도명 뒤 조사 미탐 버그도 함께 발견해 core
  [#196](https://github.com/ChoHyeonChan/maskingtape/issues/196)으로 남겼고, 지금은 머지되어 해결됨).
- **카드번호**: Visa(16자리)·Mastercard(16자리)·Amex(15자리) 계열 IIN 대역 + 하이픈/점/공백/구분자
  없음까지, 실제 발급 번호가 아닌 합성 값에 Luhn 체크섬만 유효하게 맞춘다
- **사업자등록번호**: `XXX-XX-XXXXX` 하이픈 표기(core가 지원하는 유일한 형식)에 국세청 검증
  체크섬만 유효하게 맞춘다 — 실제 발급 번호는 아니다
- **여권번호**: 구여권(`M12345678`, 문자+숫자 8자리)과 신여권(`M123A4567`, 문자+3자리+문자+4자리)
  둘 다 섞는다. core가 확신도를 문맥어("여권")로 가르므로, "여권번호 {passport}"처럼 문맥어가
  가까이 있는 템플릿과 문맥어 없이 번호만 나오는 템플릿을 모두 둬서 confidence 0.9/0.6 두
  경로를 다 검증한다
- **계좌번호**: 국민·신한·카카오뱅크·우리·하나은행 스타일 그룹 자릿수(2~4그룹, 그룹당 2~7자리,
  총 10~14자리) + 하이픈/구분자없음 표기를 섞는다. core가 문맥어 하드 게이트라, 모든 positive
  템플릿에 "계좌"/"입금"/"이체"/"은행" 등 문맥어를 반드시 포함시킨다
- **이름**: 성씨 30종 × 이름 음절 30종 조합, 통계청 다빈도 성씨 기준(특정 인물 아님). **직함만
  있고 역할어·존칭이 없는 문맥**을 이름 뒤([#213](https://github.com/ChoHyeonChan/maskingtape/issues/213),
  "홍길동 대표가")·앞([#239](https://github.com/ChoHyeonChan/maskingtape/issues/239)/[#246](https://github.com/ChoHyeonChan/maskingtape/issues/246),
  "대표 홍길동이") 둘 다 섞는다 — 성+2음절 이상 풀네임만 이 단서 하나로 인정되는 core의
  오탐 방지 가드도 함께 검증한다(단, 이 가드가 조사 삼킴으로 뚫리는 경우도 있음 —
  [#247](https://github.com/ChoHyeonChan/maskingtape/issues/247) 참고).
- **문장 맥락**: 고객센터/병원/학교/관공서/인사/배송/금융 등 10여 개 업무 시나리오, 한 문서에
  같은 종류 개인정보가 두 번 등장하는 경우(담당자 교체, 자택/직장 번호 등)도 포함

## 복합 문서 (여러 문장)

실제 문서는 한 문장으로 끝나지 않는다. `generate_multi_sentence_document()`가 서로 다른
템플릿 2~3개를 이어붙여 더 긴 문서를 만든다 — 뒤 문장에 등장하는 개인정보의 라벨 위치가
앞 문장들의 길이만큼 정확히 밀린 곳을 가리키는지(오프셋 정합성)를 검증하는 게 핵심이다.
`generate_dataset.py --multi-sentence-ratio`(기본 0.15, negative가 아닌 문서 중 비율)로 섞는 양을
조절한다.

## 난이도(difficulty) 분류

문서마다 표기 난이도를 태깅해서, 쉬운 표기와 어려운 표기에서 core의 정확도가 갈리는지
따로 측정할 수 있게 했다.

| 난이도 | 의미 | 예시 |
|---|---|---|
| `easy` | 하이픈 등 표준 구분자, 지번 주소 | `010-1234-5678`, `강남구 역삼동 12-3` |
| `hard` | 구분자 없음/국제표기, 도로명+아파트 동호수 | `01012345678`, `+82 10 1234 5678`, `테헤란로12길 3 래미안아파트 101동 502호` |
| `negative` | 개인정보 없음(오탐 측정용) | — |

`evaluate.py`는 종류(kind)별 표와 난이도별 표를 둘 다 출력한다 — 예를 들어 rrn의 전체 recall은
높은데 hard 난이도에서만 떨어진다면 "구분자 없는 표기를 놓친다"는 구체적 원인을 알 수 있다.

## 마스킹 품질(유출) 검증

`evaluate.py`는 "core가 개인정보 위치를 정확히 예측했는가"를 보는 내부 지표(precision/recall)다.
하지만 이 프로젝트의 실제 산출물은 탐지 결과가 아니라 **마스킹된 텍스트**이므로, "사용자가
받는 최종 결과물에 개인정보가 실제로 안 남았는가"도 별도로 검증할 필요가 있다.

core에는 비식별화 전략이 세 가지 있다 — `mask`(`***`, 기본), `label`(`[전화번호]`),
`pseudonym`(그럴듯한 가짜 값). `--strategy`로 골라서 검증한다.

```bash
python -m bench.evaluators.evaluate_masking bench/datasets/synth_v1.jsonl --strategy pseudonym
```

`mask`는 정답 개인정보 구간의 각 글자 위치를 원문과 하나씩 비교해 "얼마나 노출됐는지" 비율을
계산한다. `MaskAnonymizer`는 구간을 같은 길이로 제자리 치환하는 계약이라, 같은 인덱스가 같은
글자를 가리키므로 위치별 비교만으로 정확한 노출 비율(완전/부분 유출)을 알 수 있다.

- **완전 유출**(노출 비율 100%): 아예 탐지가 안 돼 원문이 통째로 남은 경우
- **부분 유출**(노출 비율 0~100%): 탐지는 됐지만 마스킹 범위 경계가 정답과 어긋나 일부만
  가려진 경우 — 탐지 자체는 됐으니 evaluate.py의 recall만 봐서는 놓치기 쉬운 결함이다.

`label`/`pseudonym`은 구간을 통째로 다른 내용으로 바꿔치기해 위치 비교 가정이 깨진다 — 실측
중 가짜 전화번호가 항상 `010-`로 시작해 원문과 우연히 같은 위치가 겹쳐 "부분 유출"로 오판되는
문제를 발견해, 이 두 전략은 원문이 결과에 통째로 남아있는지(완전 유출 vs 무유출)만 보도록
분리했다. 마스킹 후 텍스트 길이가 원본과 같은지(구조 보존)도 확인하는데, 이건 `mask`에서만
불일치가 core 회귀 버그 신호이고 `label`/`pseudonym`은 길이가 달라지는 게 정상이라 참고용이다.

500건 기준 실측 결과(#255 재측정) — mask 기준 유출률 10.9%(886건 중 97건, 전부 완전유출,
전부 `name`). **`address` 유출은 0건이다** — #248이 core #252로 고쳐지면서 마스킹 결과에서도
누락이 사라진 걸 재확인했다. `name`의 97건 유출은 전부 규칙판이 아예 못 잡은 진짜 미탐(문맥
단서 없는 이름 등)이다 — #255에서 정량화한 "차량이"류 오탐(negative 문서 33건)은 애초에
가릴 개인정보가 없는 문서라 여기 leak 집계에는 안 잡힌다(위 참고: 유출이 아니라 과다 마스킹
문제). `phone`/`email`/`rrn`/`card`/`biz_reg`/`passport`/`account`는 유출 0건, 부분 유출도
0건 — core 탐지기들이 새로 지원하게 된 표기에서도 경계까지 정확히 맞춘다는 뜻이다(체크섬 없는
RRN도 confidence 0.85로, 문맥어 있는 계좌번호도 confidence 0.6으로 여전히 탐지되므로 여기엔
안 걸린다 — 아래 confidence 절 참고). label/pseudonym도 같은 패턴(유출은 전부 `name`,
길이 보존율만 전략별로 다르게 정상 표시)을 유지한다 — 자세한 비교 방법론은 위 참고.

**pseudonym 보안 속성 검증**: `PseudonymAnonymizer`는 "가짜 주민번호/카드번호가 진짜 체크섬을
통과하면 안 된다"는 설계를 코드에 명시하고 있다 — bench 테스트가 core의 실제 검증 함수
(`_checksum_ok`, `_luhn_ok`)로 이 속성이 항상 지켜지는지 회귀 확인한다.

**pseudonym 라벨 폴백 경로 검증**([#230](https://github.com/ChoHyeonChan/maskingtape/issues/230)):
`PseudonymAnonymizer`의 `_GENERATORS`는 `name`/`phone`/`email`/`rrn`/`card`/`address` 6종에만
가짜 값 생성기를 두고, 나머지 3종(`biz_reg`/`passport`/`account` — 전부 core에 나중에 추가된
kind)은 docstring에 명시된 대로 `[라벨]` 형태로 폴백한다. 원본 유출은 없지만(직접 확인함),
이 3종은 core에 새 kind가 추가될 때마다 pseudonym.py가 갱신되지 않은 채 지금까지 방치돼
있었고 bench도 이 폴백 경로를 한 번도 검증한 적이 없었다 — 회귀 테스트로 원본 미유출과
라벨 형식을 고정해뒀다.

**label(numbered=True) 동일 개체 연결 검증**: `LabelAnonymizer(numbered=True)`는 같은 값이
반복되면 같은 번호(`[전화번호1]`)를 매겨 "동일 인물/번호"라는 문맥 정보를 보존한다고
문서화돼 있는데, bench가 이 모드를 한 번도 테스트한 적이 없었다([#164](https://github.com/ChoHyeonChan/maskingtape/issues/164)). 직접 확인해보니 판별 기준이 `Detection.text`(탐지된 원문
그대로)라서, **같은 실제 번호라도 표기(하이픈 유무 등)가 다르면 서로 다른 번호로 잘못
분리**된다(`[전화번호1]`...`[전화번호2]`) — 실제 문서에서 같은 사람 번호를 문단마다 다르게
쓰는 건 흔하므로 이 케이스에선 문서화된 약속이 지켜지지 않는다. 정상 케이스(표기 동일)와
이 한계(표기 다름) 둘 다 회귀 테스트로 고정해뒀다.

**pseudonym 동일 개체 일관성 검증**: `PseudonymAnonymizer`도 "같은 원본값은 같은 가명으로
치환되어 '그 사람'이라는 문맥이 유지된다"고 문서화돼 있는데, bench가 이 속성을 한 번도
테스트한 적이 없었다([#166](https://github.com/ChoHyeonChan/maskingtape/issues/166)). label
`numbered=True`의 [#164](https://github.com/ChoHyeonChan/maskingtape/issues/164)와 근본
원인이 같다 — 판별 기준이 `Detection.text`라서, **같은 실제 번호라도 표기가 다르면 서로
다른 가명 두 개를 받아** "그 사람" 문맥이 깨진다. 정상 케이스와 이 한계 둘 다 회귀
테스트로 고정해뒀다.

**mask(keep_head) 유출 오판 수정**: `MaskAnonymizer(keep_head=N)`는 구간 앞 N글자를 의도적으로
남기는 옵션인데, bench가 CLI/테스트 어디서도 쓴 적이 없었다([#168](https://github.com/ChoHyeonChan/maskingtape/issues/168)). 직접 재현해보니 `mask_quality.py`가 keep_head를 몰라서
**의도된 노출을 전부 "부분 유출"로 오판**했다(RRN에 keep_head=2 적용 시 유출률 100%로 표시).
이건 core 버그가 아니라 bench 자체 도구의 문제라 직접 고쳤다 — `evaluate_mask_quality()`에
`keep_head` 파라미터를 추가해 앞 N글자를 유출 판정에서 제외하고, `evaluate_masking.py`에
`--keep-head` CLI 플래그도 연결했다. keep_head보다 실제로 더 많이 새는 진짜 버그는 여전히
잡히는지도 회귀 테스트로 확인했다.

그런데 이 과정에서 core 쪽 실제 위험도 하나 발견했다: keep_head는 파이프라인 전체(모든
kind)에 적용되는 단일 값이라, **RRN(14자)을 겨냥해 keep_head=2를 설정하면 같은 파이프라인이
탐지하는 2글자 이름은 완전히 노출된다**(`min(keep_head, span_len)`이 짧은 값 전체를 삼킴) —
"일부만 보여주려던" 설정이 조용히 "이름은 전혀 안 가림"이 되는 셈이다. bench 소관이 아니라
core에 [#169](https://github.com/ChoHyeonChan/maskingtape/issues/169)로 남겼고, 이 현재
동작 자체는 회귀 테스트로 고정해뒀다(core가 고치면 테스트가 깨져서 알 수 있다).

## 신뢰도(confidence) 임계값 분석

core의 각 `Detection`에는 `confidence`(0.0~1.0)가 붙어있지만 지금까지 어디에도 쓰이지 않았다.
`confidence_analysis.py`는 이 값을 활용해 "임계값을 얼마로 잡아야 하는지" 튜닝 근거를 만든다.

```bash
python -m bench.evaluators.confidence_analysis bench/datasets/synth_v1.jsonl
```

후보 임계값마다 그보다 confidence가 낮은 예측을 버린 뒤 다시 채점해서, 임계값을 올릴수록
precision이 오르고 recall이 내려가는 트레이드오프를 표로 보여준다.

500건 기준 실측 결과(#255 재측정): 임계값 0.5 이하에서는 precision이 0.943(오탐 47건)이다 —
전부 `name` kind, confidence 정확히 0.5. **33건**(70%)이 [#255](https://github.com/ChoHyeonChan/maskingtape/issues/255)에서
새로 정량화한 잔여 위험이다 — core #252가 #247을 하드코딩 5개 부서어만 막게 고쳐서, 그 밖의
흔한 업무어("차량"/"허가"/"성과"/"안내")는 negative 문서(개인정보 없음)에서도 여전히
오탐된다. 나머지 14건은 기존에 이미 알려진 한계들이다 — 실명이 조사를 머금어 span이 한 글자
늘어나는 안전한 방향의 경계 오차(#247 수정 이후에도 남는 정상 동작, 위 참고)와 #158 잔여
패턴("민원인"/"지원자"류). 임계값 0.7부터 이 FP가 전부 걸러져 precision이 1.000이 되지만,
**recall은 0.876(임계값 0.5 이하) → 0.586(0.7) → 0.554(0.8) → 0.540(0.85) → 0.532(0.9) →
0.344(1.0)로 계속 떨어진다** — name의 규칙판 confidence 구간이 잘려나가는 게 대부분이다.

**🚨 임계값을 0.6 초과로 올리면 안 되는 진짜 이유**: 0.5→0.7 구간에서 recall이 0.876→0.586로
유독 크게 떨어지는데, name 하나만으로는 이 폭을 설명 못 한다. `account`(계좌번호)는 core가
체크섬이 없어 문맥어가 있어도 **confidence를 항상 정확히 0.6으로 고정**한다(직접 확인: 정답
account 전건 confidence 0.6). 즉 **임계값을 0.7 이상으로만 올려도 계좌번호가 100% 통째로
사라진다** — RRN(재측정 기준 threshold 0.9에서 15.6%만 걸러짐, 확률적)보다 훨씬 심각하다.
name의 오탐 몇 건을 줄이려다 가장 민감한 금융정보가 전량 유출되는 트레이드오프인 셈이다. 즉
**임계값을 높여도 얻는 정밀도 이득보다 recall 손해가(그것도 name보다 훨씬 심각한 kind에서,
그것도 100% 확정적으로) 훨씬 크므로**, 지금 core 기준으로는 기본값(필터 없음)을 유지하는 게
낫다는 근거가 된다.

**address(주소)도 confidence 임계값에 취약하다**: #196·#248이 모두 머지돼 recall 자체는
1.000으로 완전히 복구됐지만, 부분 주소(#195)가 만든 confidence 0.5(5건)/0.65(1건) 구간은
여전히 남아있다 — 정답 address 72건 기준, 임계값 0.7에서 recall이 0.917로, 0.95 이상에서는
0.792까지 떨어진다.
RRN(확률적 15.6%)·계좌번호(확정적 100%)에 이어 confidence 필터를 쓰면 안 되는 세 번째 근거다.

## 이름 탐지 방식 비교 — 규칙판 vs 하이브리드(LLM)

core에는 이름을 찾는 방법이 두 가지 있다 — `default_detectors()`(성씨 사전 + 문맥 단서 기반
규칙판만)와 `llm_detectors()`(로컬 LLM이 문맥으로 판단하고, 확신도 0.75 이상 규칙판을 안전망으로
겹치는 하이브리드). `compare_name_detectors.py`가 같은 데이터셋으로 두 방식을 나란히 비교한다.

```bash
python -m bench.evaluators.compare_name_detectors bench/datasets/synth_v1.jsonl
```

로컬 Ollama가 안 떠 있으면 하이브리드 쪽은 "LLM 사용 불가"로 표시되고 규칙판 결과만 나온다 —
CI 등 Ollama 없는 환경에서도 도구 자체는 안 죽는다.

500건 기준 실측 결과(#246 재측정, 로컬 Ollama `qwen2.5:7b`):

| 방식 | precision | recall | F1 |
|---|---|---|---|
| 규칙판 | 0.937 | 0.657 | 0.772 |
| 하이브리드(LLM) | 0.954 | 0.918 | **0.936** |

**측정 환경 메모**: 로컬 Ollama 호출이 "localhost"를 IPv6(`::1`)로 먼저 시도하는데 Ollama는
IPv4(`127.0.0.1`)에만 리스닝하고 있어 연결이 `SYN_SENT`에서 멈추는 환경 문제를 겪었다 —
`LLMNameDetector(host=...)`에 `127.0.0.1`을 명시하면 우회된다. 이 저장소 환경에서 재발할 수
있으니 하이브리드 재측정이 원인 없이 멈추면 우선 의심해볼 것.

규칙판은 앞뒤에 역할어·존칭 같은 문맥 단서가 없으면 아예 탐지하지 않도록 설계돼 오탐은
적지만(precision 高), 그만큼 단서 없는 이름은 다 놓친다(recall 低). 하이브리드는 LLM이 문맥을
직접 판단해 단서 없는 이름까지 잡아내면서(recall 0.657→0.918) recall은 크게 오르고, 이번엔
precision도 규칙판보다 오히려 살짝 높다(0.937→0.954) — 규칙판 쪽 오탐 16건 중 9건이
[#247](https://github.com/ChoHyeonChan/maskingtape/issues/247)(조사 삼킴으로 가드 우회)
때문인데, LLM은 애초에 이 정규식 가드에 의존하지 않아 그 특정 실패 유형에선 자유롭기 때문으로
보인다(다만 하이브리드도 오탐 16건으로 절대 수는 같다 — 아래 참고).

**#150·#160 반영 효과**: 규칙판 F1이 **0.676 → 0.827**까지 올랐다가(존칭 삼킴 수정 + 단어
중간 성씨 오탐 수정), #213/#239(직함-only 이름, 앞뒤 둘 다) 데이터가 섞이며 0.772로 다시
내려갔다 — 대부분 [#247](https://github.com/ChoHyeonChan/maskingtape/issues/247) 영향(위
참고). 하이브리드는 규칙판을 `min_confidence=0.75` 안전망으로만 쓰는데, #150·#160이 고친
버그들과 #247도 confidence가 0.5로 낮게 나오는 케이스라 애초에 하이브리드 결과에 거의
반영되지 않는다 — 즉 규칙판 관련 수정·버그는 **규칙 전용 모드 사용자에게 특히 의미 있다**.

**LLM은 core의 부서어 오탐 가드를 모른다**(#223 세션에서 처음 확인, 이번에도 재확인): 하이브리드
오탐도 16건이다. `LLMNameDetector`를 negative 템플릿에 개별로 돌려보면:

```python
LLMNameDetector(host="http://127.0.0.1:11434").detect("정기 이사가 참석했습니다.")
# -> [('정기', 0.9)]  LLM이 부서어 "정기"를 이름으로 오탐
LLMNameDetector(host="http://127.0.0.1:11434").detect("대표 이사가 참석했습니다.")
# -> []  #239의 새 negative 템플릿은 LLM도 정상 통과
```

규칙판의 "성+2음절 이상 풀네임만 인정" 가드(#213/#239)는 정규식으로 구현된 것이라 LLM에는 전혀
적용되지 않는다 — LLM은 문장을 보고 스스로 판단하므로, 성씨로 시작하고 문맥상 그럴듯해 보이는
부서어는 개별 모델 판단에 따라 이름으로 오인식할 수 있다(다만 모든 부서어가 그런 건 아니다 —
"이사"류는 LLM도 정상 통과). 이건 bench 데이터의 문제가 아니라 **LLM 판단의 근본적인
비결정성**이므로 core 코드로 고칠 수 있는 성격이 아니다.

## Pipeline 겹침 병합 회귀 테스트

`Pipeline._resolve_overlaps()`는 실제로 있었던 유출 사고를 막으려고 짠 로직이다 — 예전엔
주소 탐지기가 뒤따르는 주민등록번호 앞자리를 번지로 삼켜 구간이 겹치면, 겹친 탐지를
통째로 버려서 confidence 1.0짜리 주민번호 탐지가 **통보조차 안 되고 사라진 채** 뒷자리가
그대로 노출됐다. 그런데 이 함수를 검증하는 테스트가 core에도 bench에도 하나도 없었다
([#171](https://github.com/ChoHyeonChan/maskingtape/issues/171)) — 사고를 막으려고 짠
코드가 회귀해도 아무도 못 잡는 사각지대였다.

`tests/test_pipeline_overlap.py`가 가짜 Detector로 겹침 시나리오를 직접 만들어 핵심 계약을
고정한다: 겹치는 두 탐지는 합집합으로 병합되고(어느 쪽도 완전히 사라지지 않음), 부분
겹침에서는 confidence 높은 쪽이 kind를 담당하며, 겹치지 않는 탐지는 그대로 둘 다 유지된다.

**검증 중 core 쪽 비일관성도 하나 발견**: 부분 겹침은 confidence 비교로 kind를 정하는데,
**완전 포함(fully-contained) 겹침은 이 규칙이 적용되지 않고 무조건 바깥쪽(먼저 온) 구간이
kind를 차지한다.** 재현해보니 confidence 1.0짜리 rrn이 confidence 0.9짜리 address 안에
완전히 포함되면 `kind="address", confidence=0.9`로만 보고되고 rrn 존재 자체가 사라진다.
마스킹 범위 자체(넓은 쪽 전체를 가림)는 안전해서 직접 유출은 아니지만, kind에 의존하는
하류 로직(통계·로깅·정책)은 오판할 수 있다. bench 소관이 아니라
[#172](https://github.com/ChoHyeonChan/maskingtape/issues/172)로 남기고 현재 동작은
회귀 테스트로 고정해뒀다.

## 데이터셋 포맷 (생성기·평가기가 공유하는 계약)

JSONL — 한 줄에 문서 하나:

```json
{"text": "고객 홍길동 010-1234-5678 문의", "labels": [{"kind": "name", "start": 3, "end": 6}, {"kind": "phone", "start": 7, "end": 20}], "difficulty": "easy"}
```

- `start`/`end`는 파이썬 슬라이스 규약 (`text[start:end]` == 개인정보 원문)
- `kind`는 core의 `Detection.kind`와 동일한 문자열: `rrn`, `phone`, `email`, `name`, `address`, `card`, `biz_reg`, `passport`, `account`
- `difficulty`는 `easy`/`hard`/`negative` 중 하나 (없으면 evaluate.py가 `unknown`으로 취급 — 하위 호환)
- 평가 기준: span 완전 일치(exact match)로 precision / recall / F1 산출
- 포맷 변경은 팀장 승인 후 이 문서부터 갱신한다
