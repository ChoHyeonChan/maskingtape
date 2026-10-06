// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { KIND_LABELS } from "../../types/detection";

// README "지원 범위와 한계" 표와 같은 순서·같은 11종이다. core에 새 kind가 추가되면
// 이 배열도 함께 갱신한다(README.md #지원-범위와-한계 참고).
const COVERAGE_KINDS = [
  "rrn",
  "phone",
  "email",
  "address",
  "card",
  "account",
  "biz_reg",
  "passport",
  "birth_date",
  "driver_license",
  "name",
];

export function CoverageSection() {
  return (
    <section className="coverage-section" id="coverage" aria-label="탐지 범위">
      <h2>무엇을 잡나요</h2>
      <p className="coverage-section__lead coverage-section__lead--emphasis">
        11종을 규칙으로 잡고, 이름은 로컬 LLM(CLI·데스크톱)이나 웹 하이브리드(선택)로 더 잡습니다
      </p>
      <ul className="coverage-section__list">
        {COVERAGE_KINDS.map((kind) => (
          <li key={kind} className="coverage-section__item">
            {KIND_LABELS[kind]}
          </li>
        ))}
      </ul>

      {/* 루트 README와 같은 수치(#499) — 전체 F1은 「정확도」 표의 전체 행(합성 벤치 v1,
          규칙 전용), 이름 재현율은 KDPII test 500문장(학습에 안 쓴 외부 데이터, 2026-10-04)
          하이브리드 값이다. README가 바뀌면 AccuracyPage의 이름 표와 함께 갱신한다. */}
      <div className="coverage-section__stats">
        <div className="coverage-section__stat">
          <div className="coverage-section__stat-value">0.981</div>
          <div className="coverage-section__stat-label">전체 F1 (11종, 규칙 전용)</div>
        </div>
        <div className="coverage-section__stat">
          <div className="coverage-section__stat-value">0.825</div>
          <div className="coverage-section__stat-label">이름 재현율 (외부 대화 데이터, 로컬 LLM)</div>
        </div>
        <div className="coverage-section__stat">
          <div className="coverage-section__stat-value">Apache-2.0</div>
          <div className="coverage-section__stat-label">오픈소스 라이선스</div>
        </div>
      </div>
    </section>
  );
}
