// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { HYBRID_MAX_TEXT_LENGTH, hybridFellBack, type DetectionMode, type ScanModeInfo } from "../../lib/hybrid";

interface ButtonsProps {
  modeInfo: ScanModeInfo;
  textLength: number;
  rescanning: boolean;
  hybridUnavailable: boolean;
  onRescan: (mode: DetectionMode) => void;
}

// 결과 화면에서는 하이브리드를 누르는 즉시 보내므로, 보내기 전에 볼 수 있게 버튼 자체에 안내를 단다(CLAUDE.md §2-3).
const HYBRID_SEND_HINT =
  "규칙으로 먼저 가린 글을 OpenAI로 보내 남은 이름을 더 찾습니다. 규칙이 놓친 개인정보는 가린 글에 그대로 남아 함께 전송될 수 있습니다.";

/**
 * 결과 화면에서 탐지 방식을 바꿔 같은 글을 바로 다시 탐지한다(#547 후속). 규칙 전용으로 본 뒤
 * "하이브리드는 뭘 더 잡나" 비교하려고 초기화하고 다시 입력할 필요가 없다.
 * 패널 헤더 줄에 들어간다 — 따로 한 줄을 차지하면 창이 낮을 때 아래 항목 목록이 사라졌다(#715 후속).
 * 지금 방식을 다시 누르면 아무 일도 없다. 하이브리드가 실패해 규칙 결과로 돌아온 경우만 다시 시도한다.
 */
export function RescanModeButtons({ modeInfo, textLength, rescanning, hybridUnavailable, onRescan }: ButtonsProps) {
  const hybridBlocked = hybridUnavailable || textLength > HYBRID_MAX_TEXT_LENGTH;
  const current: DetectionMode = hybridBlocked ? "rule" : modeInfo.requested;

  function handleClick(mode: DetectionMode) {
    if (mode === modeInfo.requested && !hybridFellBack(modeInfo)) return;
    onRescan(mode);
  }

  return (
    <div className="rescan-mode detection-mode__group" role="group" aria-label="다시 탐지할 방식">
      <button
        type="button"
        className={`detection-mode__btn${current === "rule" ? " is-active" : ""}`}
        aria-pressed={current === "rule"}
        disabled={rescanning}
        onClick={() => handleClick("rule")}
      >
        규칙 전용
      </button>
      <button
        type="button"
        className={`detection-mode__btn${current === "hybrid" ? " is-active" : ""}`}
        aria-pressed={current === "hybrid"}
        title={hybridBlocked ? undefined : HYBRID_SEND_HINT}
        disabled={rescanning || hybridBlocked}
        onClick={() => handleClick("hybrid")}
      >
        하이브리드 (OpenAI)
      </button>
    </div>
  );
}

interface StatusProps {
  modeInfo: ScanModeInfo;
  textLength: number;
  rescanning: boolean;
  hybridUnavailable: boolean;
  error: string | null;
}

/**
 * 다시 탐지하는 중 · 다시 탐지 실패 · 하이브리드를 고를 수 없는 이유를 헤더 바로 아래 작은 글씨로 보여 준다.
 * 이번 결과가 하이브리드 실패라면 HybridStatusNotice가 이미 이유를 말하므로 막힌 이유는 쓰지 않는다.
 */
export function RescanStatus({ modeInfo, textLength, rescanning, hybridUnavailable, error }: StatusProps) {
  const quietBlockedReason = hybridFellBack(modeInfo);
  let blockedReason: string | null = null;
  if (!quietBlockedReason && hybridUnavailable) {
    blockedReason = "지금 서버에는 하이브리드 판단기가 연결돼 있지 않아 규칙 전용으로만 탐지합니다.";
  } else if (!quietBlockedReason && textLength > HYBRID_MAX_TEXT_LENGTH) {
    blockedReason = `하이브리드는 ${HYBRID_MAX_TEXT_LENGTH.toLocaleString()}자까지만 쓸 수 있어 규칙 전용으로 탐지합니다.`;
  }

  if (!rescanning && !error && !blockedReason) return null;

  return (
    <div className="rescan-status">
      {rescanning && (
        <p className="rescan-mode__hint" role="status">
          같은 글을 다시 탐지하는 중...
        </p>
      )}
      {!rescanning && blockedReason && (
        <p className="rescan-mode__hint" role="status">
          {blockedReason}
        </p>
      )}
      {error && (
        <p className="rescan-mode__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
