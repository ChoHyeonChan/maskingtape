import { ConfidenceControl } from "./ConfidenceControl";
import { KIND_COLORS, KIND_LABELS } from "../../types/detection";
import type { Detection } from "../../types/detection";

export interface DetectionRow {
  detection: Detection;
  key: string;
  snippet: string;
  masked: boolean;
}

interface Props {
  rows: DetectionRow[];
  confidenceThreshold: number;
  minThreshold: number;
  maxThreshold: number;
  thresholdStep: number;
  onThresholdChange: (next: number) => void;
  onToggle: (detection: Detection) => void;
}

/**
 * 탐지된 개인정보를 항목 하나하나로 나열하고, 각 항목의 가림/보임을 실제로 제어한다.
 * (예전 카드 그리드는 필터 UI였을 뿐 실제 마스킹 결과에 영향이 없었다 — 이제 토글이 진짜로 반영된다.)
 * 복사·다운로드는 "마스킹 결과" 패널(InputPanel) 쪽에 있다 — 최종 텍스트가 이미 거기
 * 표시되므로 내보내기 동작도 그쪽에 모아 중복을 없앴다.
 */
export function DetectionList({
  rows,
  confidenceThreshold,
  minThreshold,
  maxThreshold,
  thresholdStep,
  onThresholdChange,
  onToggle,
}: Props) {
  const maskedCount = rows.filter((row) => row.masked).length;
  const exposedCount = rows.length - maskedCount;

  if (rows.length === 0) {
    return (
      <p className="detect-empty" role="status">
        개인정보가 발견되지 않았습니다.
      </p>
    );
  }

  return (
    <div className="detect">
      <div className="detect__bulk">
        <div className="detect__bulk-head">
          <span className="detect__bulk-title">일괄 조정</span>
          <span className="detect__bulk-sublabel">확신도가 이 값 이상인 항목만 기본으로 가려집니다</span>
        </div>
        <ConfidenceControl
          value={confidenceThreshold}
          min={minThreshold}
          max={maxThreshold}
          step={thresholdStep}
          onChange={onThresholdChange}
        />
      </div>

      <p className="detect__summary" role="status">
        개인정보 {rows.length}건 발견 · {maskedCount}건 가림 · {exposedCount}건 노출
      </p>

      <ul className="detect__list" aria-label="탐지된 개인정보 목록">
        {rows.map(({ detection, key, snippet, masked }) => {
          const label = KIND_LABELS[detection.kind] ?? detection.kind;
          const confidencePct = Math.round(detection.confidence * 100);
          return (
            <li key={key} className="detect-row">
              <span
                className="detect-row__dot"
                aria-hidden="true"
                style={{ background: KIND_COLORS[detection.kind] ?? "var(--kind-fallback)" }}
              />
              <span className="detect-row__kind">{label}</span>
              <span className="detect-row__snippet">{snippet}</span>
              <span className="detect-row__confidence">{confidencePct}%</span>
              <button
                type="button"
                role="switch"
                aria-checked={masked}
                aria-label={`${label} ${snippet} ${masked ? "가려짐 — 눌러서 보이게 하기" : "보임 — 눌러서 가리기"}`}
                className={`detect-row__toggle${masked ? " is-masked" : ""}`}
                onClick={() => onToggle(detection)}
              >
                <span className="detect-row__toggle-label" aria-hidden="true">
                  {masked ? "가림" : "보임"}
                </span>
                <span className="detect-row__toggle-knob" aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
