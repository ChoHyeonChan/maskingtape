# bench — 합성 벤치마크

**담당: seoyeon ([@seoyeon056](https://github.com/seoyeon056))** · 상태: ✅ 시작 가능 (스켈레톤 머지 완료)

저작권·개인정보 걱정 없는 **자체 합성 평가 데이터셋**과 정확도(F1) 측정 스크립트. 공개 벤치마크는 이 프로젝트의 핵심 차별화 포인트다.

## 규칙 (실격 사유와 직결 — 예외 없음)

- **진짜 개인정보 절대 금지** — 모든 이름·번호·주소는 생성기로 만든 합성 데이터
- **AI Hub 등 외부 데이터셋 원본 커밋 금지**(재배포 제한) — 로컬 참고용으로만 사용

## 구성

```
generator/
  entities.py     # 종류별 합성 값 생성 (name/phone/email/rrn/address/card/biz_reg/passport)
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

500건 기준 최신 실측(#159 체크섬 없는 RRN + #160 core 단어경계 수정 반영 후 재측정, seed=42):

| kind | precision | recall | f1 | 비고 |
|---|---|---|---|---|
| phone / email / card | 1.000 | 1.000 | 1.000 | 유선전화·plus 이메일·서브도메인·복합 문장 추가돼도 그대로 유지 |
| rrn | 1.000 | 1.000 | 1.000 | [#148](https://github.com/ChoHyeonChan/maskingtape/issues/148)에서 외국인등록번호(성별코드 5~8), [#159](https://github.com/ChoHyeonChan/maskingtape/issues/159)에서 체크섬 없는(2020-10 이후 발급분) 케이스도 섞음 — 둘 다 core가 이미 지원하던 걸 처음으로 실측(탐지 자체는 체크섬과 무관해 precision/recall엔 영향 없음 — 아래 confidence 절 참고) |
| address | 1.000 | 1.000 | 1.000 | [#118](https://github.com/ChoHyeonChan/maskingtape/issues/118)에서 시/도 없는 시/군 시작 주소 positive를 추가 — core 수정([#117](https://github.com/ChoHyeonChan/maskingtape/pull/117))이 이미 머지돼 recall도 1.000으로 정상 측정됨 |
| biz_reg | 1.000 | 1.000 | 1.000 | [#123](https://github.com/ChoHyeonChan/maskingtape/issues/123)에서 새 kind로 추가 |
| passport | 1.000 | 1.000 | 1.000 | [#139](https://github.com/ChoHyeonChan/maskingtape/issues/139)에서 새 kind로 추가, [#145](https://github.com/ChoHyeonChan/maskingtape/issues/145)에서 전용 distractor(`gen_passport_like_code`)까지 추가했는데도 오탐 0건 유지 |
| name | 0.977 | 0.681 | 0.803 | 규칙판. [#150](https://github.com/ChoHyeonChan/maskingtape/pull/150)(존칭 삼킴 수정)과 [#160](https://github.com/ChoHyeonChan/maskingtape/pull/160)(단어 중간 성씨 오탐 수정, [#158](https://github.com/ChoHyeonChan/maskingtape/issues/158) 대응)으로 개선 — 아래 "이름 탐지 방식 비교" 절 참고. #158은 부분만 해결됐다 — 잔여 FP 상세는 confidence 절 참고 |

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

## 오탐(False Positive) 측정

기존에는 데이터셋 전체가 "개인정보가 있는 문서"뿐이라 재현율(recall)만 측정 가능했고,
core가 개인정보 아닌 걸 잘못 잡아내는지(정밀도, precision)는 검증 불가능했다.

`generator/distractors.py`가 주문번호·사업자등록번호·날짜·가격처럼 숫자가 섞여 있지만
개인정보는 아닌 값과, 지역번호·생년월일이 실제로는 존재하지 않는 '전화번호/주민번호 모양',
사원번호·상품 코드처럼 자릿수만 다른 '여권번호 모양' 값을 만든다. `--negative-ratio`(기본
0.25)만큼의 문서는 정답 라벨이 0개인 채로 생성되고, core가 여기서 뭔가를 탐지하면
`evaluate.py`가 그대로 FP로 집계한다.

## 문장·표기 다양성

실제 문서는 같은 개인정보라도 표기 형식이 제각각이라, 생성기도 그 다양성을 반영한다:

- **전화번호**: 하이픈(`010-1234-5678`)뿐 아니라 점(`.`)·공백·구분자 없음(`01012345678`)·
  `+82` 국제표기까지 core가 허용하는 형식을 무작위로 섞는다. **휴대폰뿐 아니라 유선전화**
  (`02-1234-5678`, `031-123-4567` 등 core `PhoneDetector`가 지원하는 지역번호 전체)도 생성한다 —
  이전엔 휴대폰만 만들어서 유선전화 경로가 한 번도 실측된 적이 없었다.
- **이메일**: 기본 표기에 더해 **plus 표기**(`user+tag@example.com`)와 **서브도메인**
  (`user@mail.example.com`)도 섞는다 — core `EmailDetector`의 로컬 파트 문자 집합(`+` 포함)과
  다중 도메인 라벨 지원을 실제로 검증한다.
- **주민번호**: 하이픈/공백/구분자 없음, 1900·2000년대 성별코드를 모두 커버. **외국인등록번호**
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
  distractor(`gen_region_mention_like`)로 별도 추가해 오탐 여부를 검증한다.
- **카드번호**: Visa(16자리)·Mastercard(16자리)·Amex(15자리) 계열 IIN 대역 + 하이픈/점/공백/구분자
  없음까지, 실제 발급 번호가 아닌 합성 값에 Luhn 체크섬만 유효하게 맞춘다
- **사업자등록번호**: `XXX-XX-XXXXX` 하이픈 표기(core가 지원하는 유일한 형식)에 국세청 검증
  체크섬만 유효하게 맞춘다 — 실제 발급 번호는 아니다
- **여권번호**: 구여권(`M12345678`, 문자+숫자 8자리)과 신여권(`M123A4567`, 문자+3자리+문자+4자리)
  둘 다 섞는다. core가 확신도를 문맥어("여권")로 가르므로, "여권번호 {passport}"처럼 문맥어가
  가까이 있는 템플릿과 문맥어 없이 번호만 나오는 템플릿을 모두 둬서 confidence 0.9/0.6 두
  경로를 다 검증한다
- **이름**: 성씨 30종 × 이름 음절 30종 조합, 통계청 다빈도 성씨 기준(특정 인물 아님)
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

500건 기준 실측 결과(#159 체크섬 없는 RRN + #160 core 단어경계 수정 반영 후 재측정) — mask 기준
유출률 11.0%(1025건 중 113건, 전부 완전유출·전부 `name`). #150 이전(15.7%, 1066건 중 167건)보다
크게 낮아졌다 — 규칙판 이름 recall이 0.529→0.681로 오르면서 완전 유출(탐지 자체 실패) 건수가
그만큼 줄었기 때문이다.
`phone`/`email`/`rrn`/`address`/`card`/`biz_reg`/`passport`는 유선전화·plus 이메일·서브도메인·
복합 문장이 섞여도 유출 0건, 부분 유출도 0건 — core 탐지기들이 새로 추가된 kind·표기·문장
구조에서도 경계까지 정확히 맞춘다는 뜻이다(체크섬 없는 RRN도 confidence 0.85로 여전히 탐지되므로
여기엔 안 걸린다 — 아래 confidence 절 참고). label/pseudonym도 같은 패턴(유출은 전부 `name`,
길이 보존율만 전략별로 다르게 정상 표시)을 유지한다 — 자세한 비교 방법론은 위 참고.

**pseudonym 보안 속성 검증**: `PseudonymAnonymizer`는 "가짜 주민번호/카드번호가 진짜 체크섬을
통과하면 안 된다"는 설계를 코드에 명시하고 있다 — bench 테스트가 core의 실제 검증 함수
(`_checksum_ok`, `_luhn_ok`)로 이 속성이 항상 지켜지는지 회귀 확인한다.

## 신뢰도(confidence) 임계값 분석

core의 각 `Detection`에는 `confidence`(0.0~1.0)가 붙어있지만 지금까지 어디에도 쓰이지 않았다.
`confidence_analysis.py`는 이 값을 활용해 "임계값을 얼마로 잡아야 하는지" 튜닝 근거를 만든다.

```bash
python -m bench.evaluators.confidence_analysis bench/datasets/synth_v1.jsonl
```

후보 임계값마다 그보다 confidence가 낮은 예측을 버린 뒤 다시 채점해서, 임계값을 올릴수록
precision이 오르고 recall이 내려가는 트레이드오프를 표로 보여준다.

500건 기준 실측 결과(#159 체크섬 없는 RRN + #160 core 단어경계 수정 반영 후 재측정): 임계값 0.5
이하에서는 precision이 0.993(오탐 6건)로 완벽하지 않다 — #150 이전(0.982, 오탐 16건)보다 줄었다.
직접 확인해보니 6건 전부 `name` kind, confidence 정확히 0.5(문맥 단서 없이 형태만으로 판단한
최저 확신도 케이스)였다. 5건은 `name.py`에 이미 문서화된 한계(성씨+이름 뒤 조사 '이'가 이름
글자와 겹쳐 함께 탐지됨, 예: "저는 양정이고"에서 "양정" 대신 "양정이"를 잡음 — 규칙만으로는
조사와 이름 글자를 구분 못 해 LLM판(name_llm)에 맡기기로 한 케이스)였다.

나머지 1건("지원자 양인훈 이력서 접수..."에서 "지원자"를 이름으로 오탐)은
[#158](https://github.com/ChoHyeonChan/maskingtape/issues/158)에서 제기한 패턴(단일 글자 존칭이
단어 경계 없이 매칭돼 뒤따르는 별개 이름의 첫 글자를 삼킴)이 그대로 남은 사례다 — 직접 재현해
확인해보니 [#160](https://github.com/ChoHyeonChan/maskingtape/pull/160)의 수정(성씨가 어절
시작일 때만 매칭)은 #158의 두 사례 중 "감지되어"(성씨가 단어 중간)만 고쳤고, "지원자"는 성씨
"지"가 이미 어절 시작이라 이 lookbehind로는 걸러지지 않는다. 즉 **#158은 부분만 해결됐다** —
"뒤따르는 이름의 첫 글자를 존칭으로 오인식"하는 suffix 쪽 원인은 아직 남아있어, 재오픈이 필요할
수 있다(이 PR 범위 아니라 코드는 안 고쳤다). 임계값 0.7부터 이 FP가 전부 걸러져 precision이
1.000이 되지만, **recall은 0.885(임계값 0.5 이하) → 0.648(0.7) → 0.620(0.8) → 0.609(0.85) →
0.592(0.9) → 0.417(1.0)로 계속 떨어진다** — name의 규칙판 confidence 구간이 잘려나가는 게
대부분이다.

**🚨 임계값을 0.85 초과로 올리면 안 되는 진짜 이유**: 0.85→0.9 구간에서 recall이 유독 더 크게
떨어지는데(0.609→0.592), 이건 name 때문이 아니다. [#159](https://github.com/ChoHyeonChan/maskingtape/issues/159)에서
추가한 "체크섬 없는(2020-10 이후 발급분) 주민등록번호"가 전부 confidence 정확히 0.85라서, 임계값을
0.9 이상으로 올리는 순간 **정답 rrn 89건 중 17건(19%)이 통째로 걸러진다** — name의 오탐 몇 건을
줄이려다 훨씬 민감한 고유식별정보(주민등록번호)가 실제로 유출되는 트레이드오프다. 즉 **임계값을
높여도 얻는 정밀도 이득보다 recall 손해가(그것도 name보다 훨씬 심각한 kind에서) 훨씬 크므로**,
지금 core 기준으로는 기본값(필터 없음)을 유지하는 게 낫다는 근거가 된다.

## 이름 탐지 방식 비교 — 규칙판 vs 하이브리드(LLM)

core에는 이름을 찾는 방법이 두 가지 있다 — `default_detectors()`(성씨 사전 + 문맥 단서 기반
규칙판만)와 `llm_detectors()`(로컬 LLM이 문맥으로 판단하고, 확신도 0.75 이상 규칙판을 안전망으로
겹치는 하이브리드). `compare_name_detectors.py`가 같은 데이터셋으로 두 방식을 나란히 비교한다.

```bash
python -m bench.evaluators.compare_name_detectors bench/datasets/synth_v1.jsonl
```

로컬 Ollama가 안 떠 있으면 하이브리드 쪽은 "LLM 사용 불가"로 표시되고 규칙판 결과만 나온다 —
CI 등 Ollama 없는 환경에서도 도구 자체는 안 죽는다.

500건 기준 실측 결과(로컬 Ollama `qwen2.5:7b` 기준, #159 체크섬 없는 RRN + #160 core 단어경계
수정까지 전부 반영 후 재측정):

| 방식 | precision | recall | F1 |
|---|---|---|---|
| 규칙판 | 0.977 | 0.681 | 0.803 |
| 하이브리드(LLM) | 0.977 | 0.900 | **0.937** |

규칙판은 앞뒤에 역할어·존칭 같은 문맥 단서가 없으면 아예 탐지하지 않도록 설계돼 오탐은
적지만(precision 高), 그만큼 단서 없는 이름은 다 놓친다(recall 低). 하이브리드는 LLM이 문맥을
직접 판단해 단서 없는 이름까지 잡아내면서(recall 0.681→0.900) F1도 더 높다
(0.803→0.937) — 이제 격차의 대부분은 "문맥 단서가 아예 없는 이름"으로 좁혀졌다.

**#150·#160 반영 효과**: 규칙판 F1이 **0.676 → 0.803**으로 크게 올랐다(존칭 삼킴 수정 +
단어 중간 성씨 오탐 수정). 반면 **하이브리드 수치는 #128 이후로 거의 변화가 없다(F1
0.933→0.937, 오차 범위)** — 하이브리드는 규칙판을 `min_confidence=0.75` 안전망으로만
쓰는데, #150·#160이 고친 버그들은 confidence가 0.5로 낮게 나오는 케이스라 애초에 하이브리드
결과에 거의 반영된 적이 없었다. 즉 두 수정은 **규칙 전용 모드 사용자에게 특히 의미 있는**
개선이다. 수치가 #150 직후(0.794/0.935)와 살짝 다른 건 #159가 데이터셋 생성 시 소비하는
난수 순서를 바꿔서다(로직은 그대로, 재현 시드 결과만 이동).

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
- `kind`는 core의 `Detection.kind`와 동일한 문자열: `rrn`, `phone`, `email`, `name`, `address`, `card`, `biz_reg`, `passport`
- `difficulty`는 `easy`/`hard`/`negative` 중 하나 (없으면 evaluate.py가 `unknown`으로 취급 — 하위 호환)
- 평가 기준: span 완전 일치(exact match)로 precision / recall / F1 산출
- 포맷 변경은 팀장 승인 후 이 문서부터 갱신한다
