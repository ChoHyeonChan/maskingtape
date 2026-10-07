// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import type { ReactNode } from "react";
import { HYBRID_MAX_TEXT_LENGTH, type DetectionMode } from "../../lib/hybrid";

interface Props {
  mode: DetectionMode;
  textLength: number;
  onChange: (mode: DetectionMode) => void;
  /** 다시 탐지하는 동안처럼 잠시 고를 수 없을 때. */
  disabled?: boolean;
  /** 버튼 바로 아래에 붙일 짧은 설명(결과 화면의 "바꾸면 다시 탐지" 안내 등). */
  hint?: ReactNode;
}

/**
 * 탐지 모드 선택(#547). 규칙 전용이 기본이고, 하이브리드는 "더 잡고 싶을 때 켜는 선택"이다.
 * 하이브리드를 고르면 OpenAI로 무엇이 가는지 안내하고(CLAUDE.md §2-3), 입력이 서버의 하이브리드
 * 상한을 넘으면 선택을 막고 이유를 보여 준다.
 */
export function DetectionModeSelector({ mode, textLength, onChange, disabled = false, hint }: Props) {
  const hybridBlocked = textLength > HYBRID_MAX_TEXT_LENGTH;
  const effectiveMode: DetectionMode = hybridBlocked ? "rule" : mode;

  return (
    <div className="detection-mode">
      <div className="detection-mode__row">
        <span className="detection-mode__label" id="detection-mode-label">
          탐지 방식
        </span>
        <div className="detection-mode__group" role="group" aria-labelledby="detection-mode-label">
          <button
            type="button"
            className={`detection-mode__btn${effectiveMode === "rule" ? " is-active" : ""}`}
            aria-pressed={effectiveMode === "rule"}
            disabled={disabled}
            onClick={() => onChange("rule")}
          >
            규칙 전용
          </button>
          <button
            type="button"
            className={`detection-mode__btn${effectiveMode === "hybrid" ? " is-active" : ""}`}
            aria-pressed={effectiveMode === "hybrid"}
            aria-describedby={hybridBlocked ? "detection-mode-blocked" : undefined}
            disabled={disabled || hybridBlocked}
            onClick={() => onChange("hybrid")}
          >
            하이브리드 (OpenAI)
          </button>
        </div>
      </div>

      {hint}

      {hybridBlocked && (
        <p className="detection-mode__blocked" id="detection-mode-blocked" role="status">
          하이브리드는 {HYBRID_MAX_TEXT_LENGTH.toLocaleString()}자까지만 쓸 수 있어 규칙 전용으로 탐지합니다. 지금{" "}
          {textLength.toLocaleString()}자입니다.
        </p>
      )}

      {effectiveMode === "hybrid" && (
        <p className="detection-mode__notice" role="note">
          하이브리드는 규칙으로 먼저 가린 글을 OpenAI로 보내 남은 이름을 더 찾습니다. 규칙이 놓친 개인정보는 가린
          글에 그대로 남아 함께 전송될 수 있으니 <strong>실제 개인정보는 넣지 마세요.</strong>
        </p>
      )}
    </div>
  );
}
