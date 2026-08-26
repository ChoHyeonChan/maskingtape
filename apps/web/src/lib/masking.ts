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
  const rows = detections.map((detection, index) => ({ detection, key: String(index), masked: true }));
  return locateDetections(text, rows, mode).text;
}

/**
 * applyMasking과 같은 최종 텍스트를 만들면서, 항목별(가림·노출 모두)로 그 항목이
 * 결과 텍스트의 어디(문자 인덱스 범위)에 있는지도 함께 돌려준다 — 오른쪽 목록에서
 * 항목에 마우스를 올렸을 때 왼쪽 "마스킹 결과" 텍스트에서 그 부분을 하이라이트하려면
 * (가려진 항목은 별표/라벨 블록 위치를, 노출된 항목은 원문 그대로의 위치를) 알아야 한다.
 */
export function locateDetections(
  text: string,
  rows: { detection: Detection; key: string; masked: boolean }[],
  mode: MaskMode,
): { text: string; ranges: Map<string, [number, number]> } {
  const ranges = new Map<string, [number, number]>();
  let cursor = 0;
  let result = "";

  const sorted = [...rows].sort(
    (a, b) => a.detection.start - b.detection.start || b.detection.end - a.detection.end,
  );

  for (const { detection, key, masked } of sorted) {
    if (detection.start < cursor) continue;
    result += text.slice(cursor, detection.start);
    const outStart = result.length;
    result += masked ? maskSegment(detection, mode) : text.slice(detection.start, detection.end);
    ranges.set(key, [outStart, result.length]);
    cursor = detection.end;
  }

  result += text.slice(cursor);
  return { text: result, ranges };
}

function maskSegment(detection: Detection, mode: MaskMode): string {
  if (mode === "label") {
    return `[${KIND_LABELS[detection.kind] ?? detection.kind}]`;
  }
  return "*".repeat(detection.end - detection.start);
}
