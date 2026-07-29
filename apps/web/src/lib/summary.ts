import type { Detection } from "../types/detection";
import { KIND_ORDER } from "../types/detection";

export interface KindCount {
  kind: string;
  count: number;
}

/** Count detections by kind while keeping familiar categories in a stable order. */
export function summarize(detections: Detection[]): KindCount[] {
  const counts = new Map<string, number>();
  for (const detection of detections) {
    counts.set(detection.kind, (counts.get(detection.kind) ?? 0) + 1);
  }

  const ordered: KindCount[] = [];
  for (const kind of KIND_ORDER) {
    const count = counts.get(kind);
    if (count) {
      ordered.push({ kind, count });
      counts.delete(kind);
    }
  }

  for (const [kind, count] of counts) {
    ordered.push({ kind, count });
  }

  return ordered;
}
