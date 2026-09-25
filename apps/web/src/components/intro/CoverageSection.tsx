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
    <section className="coverage-section" aria-label="탐지 범위">
      <h2>무엇을 잡나요</h2>
      <p className="coverage-section__lead">
        규칙(정규식·사전) + 로컬 LLM 하이브리드로 한국어 문서 속 개인정보 11종을 탐지합니다.
      </p>
      <ul className="coverage-section__list">
        {COVERAGE_KINDS.map((kind) => (
          <li key={kind} className="coverage-section__item">
            {KIND_LABELS[kind]}
          </li>
        ))}
      </ul>
    </section>
  );
}
