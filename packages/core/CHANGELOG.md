# 변경 이력

이 파일은 `maskingtape` 코어 패키지(PyPI 배포본)의 변경만 다룬다.
전체 저장소의 진행 상황은 [ROADMAP.md](../../ROADMAP.md)와 [Issues](https://github.com/ChoHyeonChan/maskingtape/issues)를 참고한다.

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
