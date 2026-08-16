import { KIND_LABELS } from "../types/detection";
import type { Detection } from "../types/detection";

export type MaskMode = "mask" | "label";

/**
 * 탐지 구간을 별표(mask) 또는 종류 라벨(label, 예: "[전화번호]")로 치환한다(#277).
 * 라벨 치환은 별표와 달리 "어떤 종류의 정보였는지"가 남아, LLM 전처리·로그 비식별화용
 * core `LabelAnonymizer`와 같은 용도로 웹 데모에서도 확인할 수 있게 한다.
 */
export function applyMasking(text: string, detections: Detection[], mode: MaskMode): string {
  if (detections.length === 0) return text;

  let cursor = 0;
  let result = "";

  for (const detection of [...detections].sort((a, b) => a.start - b.start || b.end - a.end)) {
    if (detection.start < cursor) continue;
    result += text.slice(cursor, detection.start);
    result += maskSegment(detection, mode);
    cursor = detection.end;
  }

  return result + text.slice(cursor);
}

function maskSegment(detection: Detection, mode: MaskMode): string {
  if (mode === "label") {
    return `[${KIND_LABELS[detection.kind] ?? detection.kind}]`;
  }
  return "*".repeat(detection.end - detection.start);
}
