# 변경 이력

이 파일은 `maskingtape` 코어 패키지(PyPI 배포본)의 변경만 다룬다.
전체 저장소의 진행 상황은 [ROADMAP.md](../../ROADMAP.md)와 [Issues](https://github.com/ChoHyeonChan/maskingtape/issues)를 참고한다.

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
