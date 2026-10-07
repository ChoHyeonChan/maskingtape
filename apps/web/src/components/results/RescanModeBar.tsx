// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { DetectionModeSelector } from "../input/DetectionModeSelector";
import { hybridFellBack, type DetectionMode, type ScanModeInfo } from "../../lib/hybrid";

interface Props {
  modeInfo: ScanModeInfo;
  textLength: number;
  rescanning: boolean;
  hybridUnavailable: boolean;
  error: string | null;
  onRescan: (mode: DetectionMode) => void;
}

/**
 * 결과 화면에서 탐지 방식을 바꿔 같은 글을 바로 다시 탐지한다(#547 후속). 규칙 전용으로 본 뒤
 * "하이브리드는 뭘 더 잡나" 비교하려고 초기화하고 다시 입력할 필요가 없다.
 * 지금 방식을 다시 누르면 아무 일도 없다. 하이브리드가 실패해 규칙 결과로 돌아온 경우만 다시 시도한다.
 */
export function RescanModeBar({ modeInfo, textLength, rescanning, hybridUnavailable, error, onRescan }: Props) {
  function handleChange(mode: DetectionMode) {
    if (mode === modeInfo.requested && !hybridFellBack(modeInfo)) return;
    onRescan(mode);
  }

  return (
    <div className="rescan-mode">
      <DetectionModeSelector
        mode={modeInfo.requested}
        textLength={textLength}
        onChange={handleChange}
        disabled={rescanning}
        hybridUnavailable={hybridUnavailable}
        // 이번 결과가 하이브리드 실패라면 아래 알림(HybridStatusNotice)이 이미 이유를 말한다.
        showBlockedReason={!hybridFellBack(modeInfo)}
        // 결과 화면은 높이가 빠듯해서(#715 후속) "바꾸면 다시 탐지한다"는 설명을 따로 한 줄 두지 않고
        // 이름표에 담는다. 다시 탐지하는 동안에만 상태 한 줄을 보여 준다.
        label="다시 탐지할 방식"
        compact
        hint={
          rescanning ? (
            <p className="rescan-mode__hint" role="status">
              같은 글을 다시 탐지하는 중...
            </p>
          ) : null
        }
      />
      {error && (
        <p className="rescan-mode__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
