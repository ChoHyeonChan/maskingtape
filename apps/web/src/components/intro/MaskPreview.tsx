// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { applyMasking } from "../../lib/masking";
import type { Detection } from "../../types/detection";

const PREVIEW_TEXT = "고객 홍길동님, 연락처 010-1234-5678, 이메일 hong@example.com";

// core Pipeline.scan()으로 이 문장을 직접 돌려 확인한 실제 탐지 결과다(추정 좌표가
// 아니다) — 소개 섹션 오른쪽에 "실제로 이렇게 마스킹된다"를 보여주기 위해 API 호출 없이
// 이 고정 문장에만 실제 마스킹 함수(applyMasking)를 적용한다.
const PREVIEW_DETECTIONS: Detection[] = [
  { kind: "name", start: 3, end: 6, confidence: 0.75, detector: "NameDetector" },
  { kind: "phone", start: 13, end: 26, confidence: 1, detector: "PhoneDetector" },
  { kind: "email", start: 32, end: 48, confidence: 1, detector: "EmailDetector" },
];

export function MaskPreview() {
  const masked = applyMasking(PREVIEW_TEXT, PREVIEW_DETECTIONS, "mask");

  return (
    <div className="mask-preview" aria-label="실제 마스킹 결과 미리보기">
      <div className="mask-preview__row">
        <span className="mask-preview__tag">원문</span>
        <p>{PREVIEW_TEXT}</p>
      </div>
      <div className="mask-preview__row mask-preview__row--result">
        <span className="mask-preview__tag mask-preview__tag--result">마스킹 결과</span>
        <p>{masked}</p>
      </div>
    </div>
  );
}
