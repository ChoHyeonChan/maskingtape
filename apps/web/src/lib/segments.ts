import type { Detection } from "../types/detection";

export type Segment =
  | { kind: "plain"; text: string }
  | { kind: "detection"; text: string; detection: Detection };

/** Split text into plain and detected spans for stable highlighting. */
export function buildSegments(text: string, detections: Detection[]): Segment[] {
  const sorted = [...detections].sort((a, b) => a.start - b.start);
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
