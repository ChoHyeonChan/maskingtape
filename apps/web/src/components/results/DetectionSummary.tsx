import { summarize } from "../../lib/summary";
import { KIND_LABELS } from "../../types/detection";
import type { Detection } from "../../types/detection";

interface Props {
  detections: Detection[];
  activeFilter: string | null;
  onFilterSelect: (kind: string | null) => void;
}

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
      <div className="summary__cards" aria-label="발견된 개인정보 유형">
        {counts.map(({ kind, count, minConfidence }) => {
          const confidencePct = Math.round(minConfidence * 100);
          return (
            <button
              key={kind}
              type="button"
              className={`summary-card summary-card--${kind}${activeFilter === kind ? " is-active" : ""}`}
              aria-pressed={activeFilter === kind}
              onClick={() => onFilterSelect(activeFilter === kind ? null : kind)}
            >
              <span className="summary-card__icon" aria-hidden="true" />
              <span className="summary-card__sr">
                {KIND_LABELS[kind] ?? kind} {count}건, 최소 확신도 {confidencePct}%
              </span>
              <span className="summary-card__body">
                <span>{KIND_LABELS[kind] ?? kind}</span>
                <strong>{count}건</strong>
                <span
                  className="summary-card__bar"
                  aria-hidden="true"
                  title={`최소 확신도 ${confidencePct}%`}
                >
                  <span className="summary-card__bar-fill" style={{ width: `${confidencePct}%` }} />
                </span>
              </span>
            </button>
          );
        })}
      </div>
      <details className="summary__details">
        <summary>필터 초기화</summary>
        <div className="summary__filters" aria-label="개인정보 유형 필터">
          <button
            type="button"
            className={`summary__filter${!activeFilter ? " is-active" : ""}`}
            aria-pressed={!activeFilter}
            onClick={() => onFilterSelect(null)}
          >
            전체
          </button>
          {counts.map(({ kind }) => (
            <button
              key={kind}
              type="button"
              className={`summary__filter summary__filter--${kind}${activeFilter === kind ? " is-active" : ""}`}
            aria-pressed={activeFilter === kind}
            aria-label={`${KIND_LABELS[kind] ?? kind} 보기`}
            onClick={() => onFilterSelect(kind)}
          >
            <span className={`summary__dot summary__dot--${kind}`} aria-hidden="true" />
            {KIND_LABELS[kind] ?? kind}
          </button>
          ))}
        </div>
      </details>
    </div>
  );
}
