import { summarize } from "../../lib/summary";
import { KIND_LABELS } from "../../types/detection";
import type { Detection } from "../../types/detection";

interface Props {
  detections: Detection[];
  activeFilter: string | null;
  onFilterSelect: (kind: string | null) => void;
}

/**
 * 탐지 결과 요약 + 색상 범례를 겸한다.
 * - 0건: "개인정보가 발견되지 않았습니다" (안심 메시지)
 * - N건: 총 건수 + 종류별 색 점·라벨·개수 (색이 뭘 뜻하는지 알려주는 범례 역할도 함)
 */
export function DetectionSummary({ detections, activeFilter, onFilterSelect }: Props) {
  if (detections.length === 0) {
    return (
      <p className="summary summary--clean" role="status">
        개인정보가 발견되지 않았습니다.
      </p>
    );
  }

  const counts = summarize(detections);

  return (
    <div className="summary" role="status">
      <span className="summary__total">개인정보 {detections.length}건 발견</span>
      <div className="summary__filters" aria-label="개인정보 유형 필터">
        <button
          type="button"
          className={`summary__filter${!activeFilter ? " is-active" : ""}`}
          aria-pressed={!activeFilter}
          onClick={() => onFilterSelect(null)}
        >
          전체
        </button>
        {counts.map(({ kind, count }) => (
          <button
            key={kind}
            type="button"
            className={`summary__filter summary__filter--${kind}${activeFilter === kind ? " is-active" : ""}`}
            aria-pressed={activeFilter === kind}
            onClick={() => onFilterSelect(kind)}
          >
            <span className={`summary__dot summary__dot--${kind}`} aria-hidden="true" />
            {KIND_LABELS[kind] ?? kind} {count}
          </button>
        ))}
      </div>
    </div>
  );
}
