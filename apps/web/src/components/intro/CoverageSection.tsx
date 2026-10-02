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
        규칙 + 로컬 LLM 하이브리드로 11종을 놓치지 않고 잡습니다
      </p>
      <ul className="coverage-section__list">
        {COVERAGE_KINDS.map((kind) => (
          <li key={kind} className="coverage-section__item">
            {KIND_LABELS[kind]}
          </li>
        ))}
      </ul>

      {/* README·AccuracySection과 같은 수치(#455) — 전체/이름-하이브리드 F1은
          AccuracySection의 OVERALL·ROWS와 함께 갱신한다. */}
      <div className="coverage-section__stats">
        <div className="coverage-section__stat">
          <div className="coverage-section__stat-value">0.966</div>
          <div className="coverage-section__stat-label">전체 F1 (공개 벤치마크)</div>
        </div>
        <div className="coverage-section__stat">
          <div className="coverage-section__stat-value">0.923</div>
          <div className="coverage-section__stat-label">이름 F1 (--llm 하이브리드)</div>
        </div>
        <div className="coverage-section__stat">
          <div className="coverage-section__stat-value">Apache-2.0</div>
          <div className="coverage-section__stat-label">오픈소스 라이선스</div>
        </div>
      </div>
    </section>
  );
}
