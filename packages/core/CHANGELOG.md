# 변경 이력

이 파일은 `maskingtape` 코어 패키지(PyPI 배포본)의 변경만 다룬다.
전체 저장소의 진행 상황은 [ROADMAP.md](../../ROADMAP.md)와 [Issues](https://github.com/ChoHyeonChan/maskingtape/issues)를 참고한다.

## 0.4.0 (2026-10-02)

0.3.0 뒤로 core에 들어간 유출 수정을 묶었다. 이름·주소·번호를 조금만 다르게 써도 원문이 그대로 남던 경우가 대부분이다.
합성 벤치(`synth_v1` 500건, 규칙 전용)에서 이름 재현율이 0.668에서 0.932로 올라, 놓친 이름이 127개에서 26개로 줄었다.
전체 F1은 0.911에서 0.981이다. 여기에는 벤치 문장 틀에 쓰인 라벨 어휘를 더한 몫([#537](https://github.com/ChoHyeonChan/maskingtape/issues/537))이 섞여 있어,
실제 문서에서는 상한으로 읽어야 한다. 0.3.x 사용자는 **업그레이드를 권한다**.

아래 예시 입력(합성 값)은 모두 0.3.0에서 원문이 남고 0.4.0에서 가려지는 것을 직접 돌려 확인했다.

### 보안 (미탐 = 유출)

**표기 변형**

- **전각 숫자·폭 없는 공백·대시 변형·자모 분해 표기에서 탐지를 통째로 비껴가던 문제** ([#490](https://github.com/ChoHyeonChan/maskingtape/issues/490))
  `주민번호 ８００１０１-１２３４５６０`, `전화 010−1234−5678`(U+2212 빼기 기호), 자모로 분해한(NFD) `고객 김민수님`이 원문 그대로 남았다.
  원문과, 표기를 정리한 사본 둘 다에서 찾아 합친다. 원문에서 찾은 결과는 그대로 두므로 정리 때문에 덜 가리는 일은 없다.

**이름**

- **서식 역할어·실무 직함 뒤 이름** ([#394](https://github.com/ChoHyeonChan/maskingtape/issues/394), [#580](https://github.com/ChoHyeonChan/maskingtape/issues/580)):
  `총무 김민수 확인`, `담당 상담원 김민수`. 역할어(환자명·예금주·지원자 등)와 직함(총무·매니저·간호사 등) 어휘를 넓혔다.
- **양식 라벨의 흔한 변형** ([#491](https://github.com/ChoHyeonChan/maskingtape/issues/491)):
  `성명 : 홍길동`(콜론 앞 공백), `| 성명 | 홍길동 |`(표 칸), 사전에 없는 성씨(`성명: 류서윤`)
- **표 머리행의 이름 열** ([#526](https://github.com/ChoHyeonChan/maskingtape/issues/526)):
  CSV·TSV·마크다운 표의 머리행이 `이름`·`성명` 등이면 아래 행의 이름을 가린다. 전에는 같은 행의 전화번호·이메일만 가려지고 이름은 남았다.
- **슬래시로 나눈 명단** ([#581](https://github.com/ChoHyeonChan/maskingtape/issues/581)): `김민수 / 개발팀 / 010-3456-7890`
- **다음 줄 라벨에 먹히던 여러 줄 양식의 이름** ([#662](https://github.com/ChoHyeonChan/maskingtape/issues/662)):
  `참석자: 송준경⏎작성자: 문양석`에서 다음 줄 라벨을 앞 이름의 뒤 단서로 읽어 `문양석`이 통째로 남았다.
  두 칸 `성명 | 김민수⏎담당자 | 이서연`은 라벨 칸(`담당자`)을 이름으로 가리고 `이서연`은 남겼다.
- **끝 글자가 조사처럼 생긴 이름** ([#579](https://github.com/ChoHyeonChan/maskingtape/issues/579)): `신청인 이하은`
- **업무 문서 제목형 라벨** ([#537](https://github.com/ChoHyeonChan/maskingtape/issues/537)): `이력서 접수: 전혜호, 생일 1986-10-02`.
  벤치 문장 틀에 있던 라벨이라 벤치 수치를 올린 몫이 크다.
- **판결문의 판사·검사·증인, 띄어 쓴 받는 사람** ([#663](https://github.com/ChoHyeonChan/maskingtape/issues/663)):
  `판사 정재아`, `검사 황수재(기소, 공판)`, `증인 문양석의 증언에 의하면`, `받는 사람: 송준경 <…>`,
  `제 이름은 황은민이고요,`가 통째로 남았다. 판사·검사·증인은 일반어와 겹쳐 이름 앞에서, 이름 뒤가 낱말
  경계일 때만 받는다(`검사 진단서를`·`증인 신문이 열렸다`·`유전자 검사를`은 이름이 아니다).

**주소**

- **시·군 뒤에 바로 오는 도로명** ([#425](https://github.com/ChoHyeonChan/maskingtape/issues/425)): `김포시 김포대로 123`이 통째로 남았다.
- **세종 축약형과 읍·면 부분 유출** ([#465](https://github.com/ChoHyeonChan/maskingtape/issues/465)):
  `세종 한누리대로 2130`이 통째로 남고, `세종특별자치시 장군면 대학길 12`는 `면 대학길 12`가 남았다.
- **두 칸 이상 공백이나 줄바꿈으로 나눈 주소** ([#492](https://github.com/ChoHyeonChan/maskingtape/issues/492)):
  `서울특별시  강남구  테헤란로  123`에서 시/도만 가려졌다.
- **시/도 없이 구로 시작하는 주소** ([#492](https://github.com/ChoHyeonChan/maskingtape/issues/492), [#511](https://github.com/ChoHyeonChan/maskingtape/issues/511)):
  `주소: 강남구 테헤란로 123`, `강남구 역삼동 12 (배송지)`, `배송지 목록` 아래 줄마다 이어지는 구 주소.
  `인구 이동 강남구 역삼동 1.2%` 같은 통계 문장은 잡지 않도록, 앞뒤나 목록 머리에 주소 단서가 있을 때만 받는다.

**주민등록번호·생년월일**

- **날짜 표기** ([#399](https://github.com/ChoHyeonChan/maskingtape/issues/399), [#493](https://github.com/ChoHyeonChan/maskingtape/issues/493)):
  `생년월일 95.03.22`(2자리 연도), `생년월일: 1999. 7. 21.`(공문서 날짜)
- **8자리 앞자리 주민등록번호** ([#508](https://github.com/ChoHyeonChan/maskingtape/issues/508)): `생년월일 19800101-1234567`이 통째로 남았다.
- **뒷자리를 가린 주민등록번호** ([#528](https://github.com/ChoHyeonChan/maskingtape/issues/528)): `주민번호 800101-1******`의 앞자리(생년월일)가 통째로 남았다.
- **드문 구분자** ([#529](https://github.com/ChoHyeonChan/maskingtape/issues/529)): `800101/1234567`처럼 `/`·`·`·`_` 등으로 나눈 번호

**전화·계좌·카드·여권**

- 전화: `TEL 02)555-1234`([#493](https://github.com/ChoHyeonChan/maskingtape/issues/493)), `(+82) 10-1234-5678`·`+820212345678`([#509](https://github.com/ChoHyeonChan/maskingtape/issues/509))
- 계좌: 은행 약칭만 붙은 `신한 110-123-456789`와 끝 묶음이 한 자리인 `새마을금고 9002-1234-5678-1`([#472](https://github.com/ChoHyeonChan/maskingtape/issues/472)),
  공백·점으로 나눈 `입금 계좌 1002 123 456789`([#474](https://github.com/ChoHyeonChan/maskingtape/issues/474)),
  라벨에 하이픈으로 붙은 `입금계좌-110-123-456789`([#493](https://github.com/ChoHyeonChan/maskingtape/issues/493))
- 카드: 19자리 `6212 3456 7890 1234 569`, 구분자가 섞인 `카드 4111-1111 1111-1111`([#493](https://github.com/ChoHyeonChan/maskingtape/issues/493)).
  두 장을 이어 쓴 `카드 4111-1111 1111-1111 4111 1111 1111 1111`은 `4111-1111 1111-`과 끝 묶음 `1111`이 남았다([#510](https://github.com/ChoHyeonChan/maskingtape/issues/510))
- 여권: `여권번호 M 12345678`([#493](https://github.com/ChoHyeonChan/maskingtape/issues/493))

**로컬 LLM과 치환 전략**

- **`--llm` 원문이 PC 밖으로 나갈 수 있던 경로** ([#468](https://github.com/ChoHyeonChan/maskingtape/issues/468)):
  프록시 설정(`HTTP_PROXY`, Windows 시스템 프록시)을 따라가거나, 클라우드 모델(`gpt-oss:120b-cloud` 등)이 원문을 ollama.com으로 넘기거나,
  `http://evil.com@localhost:11434`처럼 검사한 주소와 실제 접속 주소가 다를 수 있었다. 원문을 보내기 전에 모두 막는다.
  리다이렉트도 따라가지 않는다. 0.3.0은 302를 받으면 원문 없이 다른 곳에 다시 요청해 그 응답으로 이름을 덜 가릴 수 있었다.
- **겹친 탐지를 치환하다 원문 글자를 남기던 문제** ([#494](https://github.com/ChoHyeonChan/maskingtape/issues/494)):
  탐지 목록을 직접 넘기는 라이브러리 호출에서 `LabelAnonymizer`가 `연락처 [전화번호]름]8 끝`처럼 원문 끝 글자를 남겼다.
  `PseudonymAnonymizer`도 같았다. 치환하기 전에 겹친 탐지를 합친다. `Pipeline`을 거친 결과는 원래 겹침이 없어 영향이 없었다.
- **가명이 원본과 같던 문제** ([#494](https://github.com/ChoHyeonChan/maskingtape/issues/494)):
  `고객 김서준님`의 가명이 시드 2,000개 중 3개에서 `김서준` 그대로였다. 원본과 같거나 서로 품는 가명, 같은 호출에서 이미 쓴 가명은 다시 뽑는다.

### 변경

- **로컬 LLM 접속** ([#468](https://github.com/ChoHyeonChan/maskingtape/issues/468))
  - 기본 주소가 `http://localhost:11434`에서 `http://127.0.0.1:11434`로 바뀌었다. Windows가 localhost를 IPv6로 먼저 시도해 요청마다 약 2초를 기다렸기 때문이다.
  - 프록시 설정을 무시하고 직접 연결한다. 리다이렉트는 따라가지 않는다.
  - 원문을 보내기 전에 모델 정보(`/api/show`)를 한 번 더 요청해, 원격 모델로 이어진 로컬 별칭을 거부한다.
  - 원격 주소처럼 클라우드 모델과 `@`가 든 주소도 탐지기를 만들 때 `ValueError`를 낸다. CLI는 안내를 출력하고 종료 코드 2로 끝난다.
- **LLM 하이브리드의 규칙 안전망** ([#476](https://github.com/ChoHyeonChan/maskingtape/issues/476)): 확신도 0.75 이상만 남기던 규칙 이름 탐지를 전부 함께 쓴다.
  벤치(qwen2.5:7b)에서 놓친 이름이 30개에서 21개로 줄고, 오탐은 21개에서 28개로 늘었다.
- **LLM 호출 범위와 응답 검증** ([#494](https://github.com/ChoHyeonChan/maskingtape/issues/494)): 사전에 없는 성씨로 시작하는 문장도 LLM에 보낸다.
  응답의 이름 목록에 문자열이 아닌 값이 있으면 `TypeError`를 낸다. 메시지에는 받은 형태만 적고 이름은 적지 않는다. 같은 이름은 한 번만 찾는다.
- **`MaskAnonymizer`도 치환 전에 겹친 탐지를 합친다** ([#520](https://github.com/ChoHyeonChan/maskingtape/issues/520)). `Pipeline` 결과에는 출력 변화가 없다.
- **가명 어휘가 모자라면 라벨로 가린다** ([#494](https://github.com/ChoHyeonChan/maskingtape/issues/494)): 한 호출에 서로 다른 이름이 수백 개면 뒤쪽 이름은 가명 대신 `[이름]`이 된다. 원본은 남지 않는다.
- **성씨+직함은 성씨만 가린다** ([#677](https://github.com/ChoHyeonChan/maskingtape/issues/677)): `고객 김부장님`이 `고객 *부장님`이 된다. 전에는 `김부장`을 세 글자 이름으로 보고 직함까지 가렸다.
  뒤에 나열한 이름은 그대로 가린다(`참석자: 김부장, 이서연, 박지훈` → `참석자: *부장, ***, ***`).
- `Detector`에 `calls_model` 속성이 생겼다(기본 `False`). 모델을 부르는 비싼 탐지기는 `True`로 두면, `Pipeline`이 표기를 정리해 다시 찾을 때 되도록 정리본에서만 부른다([#490](https://github.com/ChoHyeonChan/maskingtape/issues/490)).
- 선택 의존성 `bench-baselines`(scrubadub)가 패키지 메타데이터에 생겼다. 저장소 벤치에서 다른 도구와 비교할 때만 쓰고, 설치하지 않으면 영향이 없다.

### 수정

- CLI 출력이 Windows에서 CRLF 줄바꿈을 `\r\r\n`으로 바꾸던 문제 ([#494](https://github.com/ChoHyeonChan/maskingtape/issues/494)). 데스크톱 앱이 이 출력을 저장하면 CSV 행 수가 두 배가 됐다.
- 일반 낱말을 이름으로 가리던 오탐: `고객님께`의 `고객`([#450](https://github.com/ChoHyeonChan/maskingtape/issues/450)), `이름 정밀 탐지`의 `정밀`([#484](https://github.com/ChoHyeonChan/maskingtape/issues/484))

### 기타

- 모든 소스 파일에 저작권 줄(`SPDX-FileCopyrightText`)을 더했다 ([#437](https://github.com/ChoHyeonChan/maskingtape/issues/437)). 라이선스 줄(`SPDX-License-Identifier`)은 전부터 있었다.

## 0.3.0 (2026-09-15)

주소에서 건물번호가 새던 부분 유출과, 주소가 반복되는 긴 입력에서 처리가 수십 초씩 걸리던 문제를 고쳤다.
README에 공개했던 미탐 표기 다섯 가지도 이제 잡는다. 0.2.0 사용자는 **업그레이드를 권한다**.

### 보안 (미탐 = 유출)

- **주소가 동/도로명 자리에서 끊겨 뒤의 도로명·건물번호가 남던 문제** ([#423](https://github.com/ChoHyeonChan/maskingtape/issues/423))
  `전라남도 해남군 해남읍 중앙1로 330`을 `…해남읍`까지만 가려서 `중앙1로 330`이 원문으로 남았다.
  같은 자리에서 새던 형태를 모두 한 구간으로 잡는다. 읍·면 뒤의 도로명과 리(`해남읍 중앙1로 330`, `양평읍 양근리 123`),
  동·리가 든 도로명(`대동로 12`), 숫자가 든 도로명·행정동·N가 동(`센텀2로 25`, `신림2동 123-4`, `을지로3가 12`),
  동 뒤의 도로명(`역삼동 테헤란로 123`), 가길(`올림픽로35가길 10`)이다.
  예전 규칙보다 덜 가리는 입력이 생기지 않도록 해석 순서를 짰다.
- **시/도 축약형 주소 미탐** ([#396](https://github.com/ChoHyeonChan/maskingtape/issues/396))
  `서울 강남구 테헤란로 123`처럼 시/도를 줄여 쓴 주소를 잡는다. `서울 사람`, `경기 침체` 같은 지역 언급은
  잡지 않도록, 뒤에 시/군/구와 동·도로명이 이어질 때만 주소로 본다.
- **전화번호 괄호 표기 미탐** ([#397](https://github.com/ChoHyeonChan/maskingtape/issues/397)): `(010) 1234-5678`, `(02) 123-4567`
- **여권번호 소문자 표기 미탐** ([#398](https://github.com/ChoHyeonChan/maskingtape/issues/398)): `m12345678`
- **이메일 한글 로컬파트 미탐** ([#400](https://github.com/ChoHyeonChan/maskingtape/issues/400)): `홍길동@example.com`
- **주소가 반복되는 긴 입력에서 처리 시간이 제곱으로 늘던 문제** ([#426](https://github.com/ChoHyeonChan/maskingtape/issues/426))
  겹침 검사가 후보마다 앞서 잡은 구간 전체를 훑어서, 주소가 반복되는 40만 자 입력이 80초 넘게 걸렸다.
  이분 탐색으로 바꿔 같은 입력이 1초 안에 끝난다. 탐지 결과는 그대로다.

### 변경

- 로컬 LLM 이름 탐지기가 모델 응답에 이름 목록이 없을 때 던지는 예외가 `RuntimeError`에서 `TypeError`로 바뀌었다
  ([#416](https://github.com/ChoHyeonChan/maskingtape/pull/416)). 이 예외를 `RuntimeError`로 잡던 코드는 `TypeError`도 함께 잡아야 한다.
  Ollama 연결 실패와 JSON 파싱 실패는 그대로 `RuntimeError`다.

### 수정

- `--llm` CLI가 형식이 틀린 모델 응답에서 트레이스백을 내고 종료되던 문제 ([#420](https://github.com/ChoHyeonChan/maskingtape/issues/420)).
  이제 안내 메시지를 출력하고 종료 코드 1로 끝난다. 메시지에는 실제로 받은 형태(`names=str` 등)만 적고,
  응답 본문은 개인정보가 섞일 수 있어 적지 않는다. 규칙 전용 모드의 예외는 코드 버그를 가리지 않도록 그대로 보여 준다.

## 0.2.0 (2026-08-25)

탐지 종류가 9종에서 **11종**으로 늘고, 개인정보가 새던 미탐 버그 두 건을 고쳤다.
0.1.0 사용자는 **업그레이드를 권한다** — 아래 보안 수정이 실제 유출 경로였다.

### 보안 (미탐 = 유출)

- **주민등록번호·전화번호의 분리자 변형을 놓치던 문제** ([#339](https://github.com/ChoHyeonChan/maskingtape/issues/339))
  `800101-1234560`은 잡았지만 `800101–1234560`(en-dash), `800101 - 1234560`(공백-대시-공백),
  `800101  1234560`(더블 스페이스)은 **탐지하지 못하고 원문 그대로 통과**시켰다.
  분리자 패턴을 `[-.\s–—]{0,3}`으로 넓혀 세 변형을 모두 잡는다. 전화번호도 같은 수정을 적용했다.

- **이름 끝 글자를 존칭으로 잘못 삼키던 문제** ([#340](https://github.com/ChoHyeonChan/maskingtape/issues/340))
  "김민양"에서 `양`을, "박준군"에서 `군`을 존칭으로 보고 이름을 `김민`·`박준`으로 잘라
  실제 이름 글자가 마스킹되지 않고 남았다. 존칭 목록에서 `양`·`군`을 뺐다
  (`님`·`씨`는 유지 — [#147](https://github.com/ChoHyeonChan/maskingtape/issues/147) 회귀 방지).

- **생년월일 정규식 ReDoS** ([#289](https://github.com/ChoHyeonChan/maskingtape/issues/289))
  중첩 수량자로 입력 길이에 대해 지수 시간이 걸릴 수 있던 패턴을 상한이 있는 형태로 교체.

### 추가

- **운전면허번호 탐지기** ([#267](https://github.com/ChoHyeonChan/maskingtape/issues/267)) — 12자리 숫자 + 지역코드(11~26·28).
  체크섬이 공개되지 않아 형식만으로 판단하므로 confidence는 0.85로 고정된다.
- **생년월일 탐지기** ([#266](https://github.com/ChoHyeonChan/maskingtape/issues/266)) — 문맥 앵커(생년월일·생일 등) 하드 게이트, confidence 0.9 고정.
- 주소에서 **번지 표기**(`123번지`)와 번지 뒤 콤마가 낀 동/호를 잡는다 ([#265](https://github.com/ChoHyeonChan/maskingtape/issues/265), [#340](https://github.com/ChoHyeonChan/maskingtape/issues/340)).

### 수정

- 라벨 치환 전략에서 `driver_license`·`birth_date` 라벨이 빠져 kind 이름이 그대로 노출되던 문제.
- 이름 탐지의 부서어 오탐 가드가 조사에 뚫리던 문제 ([#247](https://github.com/ChoHyeonChan/maskingtape/issues/247)).
- 주소 뒤 계사 어미("입니다"/"예요")에서 미탐 ([#248](https://github.com/ChoHyeonChan/maskingtape/issues/248)).

### 성능

- 로컬 LLM 이름 탐지의 콜드스타트 제거 — Ollama `keep_alive`로 모델을 상주시킨다 ([#269](https://github.com/ChoHyeonChan/maskingtape/issues/269)).

### 그 외

- 모든 소스 파일에 `SPDX-License-Identifier: Apache-2.0` 헤더 추가.
- 배포물(wheel/sdist)에 LICENSE 원문 포함.

## 0.1.0 (2026-08-11)

첫 공개 배포. 주민등록번호(체크섬 검증)·전화번호·이메일·주소·신용카드(Luhn)·계좌번호·
사업자등록번호·여권번호·이름 9종 탐지, 마스킹/라벨/가명처리 전략, CLI 제공.
