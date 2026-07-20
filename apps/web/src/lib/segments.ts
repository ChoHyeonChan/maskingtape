import type { Detection } from "../types/detection";

export type Segment =
  | { kind: "plain"; text: string }
  | { kind: "detection"; text: string; detection: Detection };

/**
 * 원문 + 탐지 목록을 하이라이트 렌더링용 조각으로 쪼갠다.
 * 겹치는 구간은 core Pipeline이 이미 정리해 보내지만, 혹시 겹쳐 있으면 먼저 나온(start가 빠른) 것을 우선한다.
 */
export function buildSegments(text: string, detections: Detection[]): Segment[] {
  const sorted = [...detections].sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];
  let cursor = 0;

  for (const d of sorted) {
    if (d.start < cursor) continue; // 겹치는 구간 방어
    if (d.start > cursor) {
      segments.push({ kind: "plain", text: text.slice(cursor, d.start) });
    }
    segments.push({ kind: "detection", text: text.slice(d.start, d.end), detection: d });
    cursor = d.end;
  }

  if (cursor < text.length) {
    segments.push({ kind: "plain", text: text.slice(cursor) });
  }

  return segments;
}
