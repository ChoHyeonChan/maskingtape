import type { Detection } from "../types/detection";

export type Segment =
  | { kind: "plain"; text: string }
  | { kind: "detection"; text: string; detection: Detection };

/** Split text into plain and detected spans for stable highlighting. */
export function buildSegments(text: string, detections: Detection[]): Segment[] {
  // start가 같은 두 탐지가 겹치면 더 긴 쪽을 남긴다 — applyMasking()과 반드시 같은 규칙을
  // 써야 한다. 규칙이 다르면 여기 하이라이트 미리보기는 A를 보여주는데 복사·다운로드되는
  // 실제 마스킹 결과는 B를 가리는 식으로, 화면에서 검토한 내용과 내보낸 결과가 어긋난다.
  const sorted = [...detections].sort((a, b) => a.start - b.start || b.end - a.end);
  const segments: Segment[] = [];
  let cursor = 0;

  for (const detection of sorted) {
    if (detection.start < cursor) continue;
    if (detection.start > cursor) {
      segments.push({ kind: "plain", text: text.slice(cursor, detection.start) });
    }
    segments.push({ kind: "detection", text: text.slice(detection.start, detection.end), detection });
    cursor = detection.end;
  }

  if (cursor < text.length) {
    segments.push({ kind: "plain", text: text.slice(cursor) });
  }

  return segments;
}
