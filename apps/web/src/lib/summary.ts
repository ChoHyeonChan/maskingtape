import type { Detection } from "../types/detection";
import { KIND_ORDER } from "../types/detection";

export interface KindCount {
  kind: string;
  count: number;
}

/**
 * 탐지 목록을 종류별 개수로 집계한다.
 * KIND_ORDER 순으로 정렬하고, 목록에 없는 종류는 뒤에 붙인다 (순수 함수 — 테스트 용이).
 */
export function summarize(detections: Detection[]): KindCount[] {
  const counts = new Map<string, number>();
  for (const d of detections) {
    counts.set(d.kind, (counts.get(d.kind) ?? 0) + 1);
  }

  const ordered: KindCount[] = [];
  for (const kind of KIND_ORDER) {
    const count = counts.get(kind);
    if (count) {
      ordered.push({ kind, count });
      counts.delete(kind);
    }
  }
  // KIND_ORDER에 없는 미지의 종류가 있으면 등장 순서대로 뒤에 붙인다
  for (const [kind, count] of counts) {
    ordered.push({ kind, count });
  }
  return ordered;
}
