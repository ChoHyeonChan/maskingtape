# 오픈소스 PII 도구 비교 리포트

- 데이터셋: `bench/datasets/synth_v1.jsonl` (500건, 합성 데이터)
- 생성 시각: 2026-10-01 04:41 UTC
- 평가 방식: span 완전 일치(exact match) 기준 precision/recall/F1/F2
- 비교 대상: 로컬 실행 오픈소스 도구만 사용. 상용 API 모델·비상업 전용 모델은 제외.

## 비교 도구와 라이선스

- maskingtape-rules 0.3.0: Apache-2.0, https://github.com/ChoHyeonChan/maskingtape
- scrubadub 2.0.1: MIT metadata / Apache-2.0 classifier, https://github.com/LeapBeyond/scrubadub

## 엔티티 매핑

| tool | raw entity | maskingtape kind |
|---|---|---|
| maskingtape-rules | account | account |
| maskingtape-rules | address | address |
| maskingtape-rules | birth_date | birth_date |
| maskingtape-rules | biz_reg | biz_reg |
| maskingtape-rules | card | card |
| maskingtape-rules | driver_license | driver_license |
| maskingtape-rules | email | email |
| maskingtape-rules | name | name |
| maskingtape-rules | passport | passport |
| maskingtape-rules | phone | phone |
| maskingtape-rules | rrn | rrn |
| scrubadub | credit_card | card |
| scrubadub | email | email |
| scrubadub | phone | phone |

## 전체 요약

| tool | precision | recall | f1 | f2 | tp | fp | fn |
|---|---|---|---|---|---|---|---|
| maskingtape-rules | 0.988 | 0.974 | 0.981 | 0.977 | 969 | 12 | 26 |
| scrubadub | 0.569 | 0.062 | 0.112 | 0.076 | 62 | 47 | 933 |

## maskingtape-rules kind별 결과

| group | precision | recall | f1 | f2 | tp | fp | fn |
|---|---|---|---|---|---|---|---|
| account | 1.000 | 1.000 | 1.000 | 1.000 | 37 | 0 | 0 |
| address | 1.000 | 1.000 | 1.000 | 1.000 | 56 | 0 | 0 |
| birth_date | 1.000 | 1.000 | 1.000 | 1.000 | 52 | 0 | 0 |
| biz_reg | 1.000 | 1.000 | 1.000 | 1.000 | 20 | 0 | 0 |
| card | 1.000 | 1.000 | 1.000 | 1.000 | 26 | 0 | 0 |
| driver_license | 1.000 | 1.000 | 1.000 | 1.000 | 43 | 0 | 0 |
| email | 1.000 | 1.000 | 1.000 | 1.000 | 70 | 0 | 0 |
| name | 0.967 | 0.932 | 0.949 | 0.939 | 357 | 12 | 26 |
| passport | 1.000 | 1.000 | 1.000 | 1.000 | 33 | 0 | 0 |
| phone | 1.000 | 1.000 | 1.000 | 1.000 | 207 | 0 | 0 |
| rrn | 1.000 | 1.000 | 1.000 | 1.000 | 68 | 0 | 0 |
| **overall** | **0.988** | **0.974** | **0.981** | **0.977** | 969 | 12 | 26 |

## scrubadub kind별 결과

| group | precision | recall | f1 | f2 | tp | fp | fn |
|---|---|---|---|---|---|---|---|
| account | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 37 |
| address | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 56 |
| birth_date | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 52 |
| biz_reg | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 20 |
| card | 1.000 | 0.346 | 0.514 | 0.398 | 9 | 0 | 17 |
| driver_license | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 43 |
| email | 0.343 | 0.343 | 0.343 | 0.343 | 24 | 46 | 46 |
| name | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 383 |
| passport | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 33 |
| phone | 0.967 | 0.140 | 0.245 | 0.169 | 29 | 1 | 178 |
| rrn | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 68 |
| **overall** | **0.569** | **0.062** | **0.112** | **0.076** | 62 | 47 | 933 |
