// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { hybridFailureMessage, hybridFellBack, isLlmDetection, type ScanModeInfo } from "../../lib/hybrid";
import type { Detection } from "../../types/detection";

interface Props {
  modeInfo: ScanModeInfo;
  detections: Detection[];
}

/**
 * 하이브리드로 탐지했을 때의 결과 알림(#547). 실패해 규칙 결과로 돌아왔으면 조용히 넘어가지 않고
 * 이유와 함께 알리고(CLAUDE.md §2-3), 성공했으면 LLM이 더 찾은 이름 수를 보여 준다.
 * 규칙 전용으로 탐지했으면 아무것도 그리지 않는다.
 */
export function HybridStatusNotice({ modeInfo, detections }: Props) {
  if (modeInfo.requested !== "hybrid") return null;

  if (hybridFellBack(modeInfo)) {
    return (
      <p className="hybrid-status hybrid-status--fallback" role="alert">
        <strong>하이브리드 판단에 실패해 규칙 전용 결과만 보여 줍니다.</strong> {hybridFailureMessage(modeInfo.failureCode)}
      </p>
    );
  }

  const llmCount = detections.filter(isLlmDetection).length;
  return (
    <p className="hybrid-status" role="status">
      {llmCount > 0 ? (
        <>
          하이브리드: 규칙이 놓친 이름 <strong>{llmCount}건</strong>을 더 찾았습니다(목록의{" "}
          <span className="llm-badge">LLM</span>).
        </>
      ) : (
        "하이브리드: OpenAI 판단기가 더 찾은 이름은 없습니다."
      )}
    </p>
  );
}
