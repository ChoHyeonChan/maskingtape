import type { Detection } from "../types/detection";
import { KIND_ORDER } from "../types/detection";

export interface KindCount {
  kind: string;
  count: number;
  /** 이 종류 안에서 가장 낮은 확신도 — 평균이 아니라 최솟값을 쓴다(#237).
   *  평균을 쓰면 낮은 확신도 하나가 묻힐 수 있어, "이 종류를 얼마나 믿을 수 있는가"를
   *  보수적으로(최악의 경우 기준으로) 보여준다. */
  minConfidence: number;
}

/** Count detections by kind while keeping familiar categories in a stable order. */
export function summarize(detections: Detection[]): KindCount[] {
  const stats = new Map<string, { count: number; minConfidence: number }>();
  for (const detection of detections) {
    const current = stats.get(detection.kind);
    if (current) {
      current.count += 1;
      current.minConfidence = Math.min(current.minConfidence, detection.confidence);
    } else {
      stats.set(detection.kind, { count: 1, minConfidence: detection.confidence });
    }
  }

  const ordered: KindCount[] = [];
  for (const kind of KIND_ORDER) {
    const stat = stats.get(kind);
    if (stat) {
      ordered.push({ kind, ...stat });
      stats.delete(kind);
    }
  }

  for (const [kind, stat] of stats) {
    ordered.push({ kind, ...stat });
  }

  return ordered;
}
