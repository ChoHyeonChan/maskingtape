import { DetectionSummary } from "./DetectionSummary";
import { HighlightedText } from "./HighlightedText";
import type { Detection } from "../../types/detection";

interface Props {
  scanned: { text: string; detections: Detection[] } | null;
  activeFilter: string | null;
  scanRun: number;
  onFilterSelect: (kind: string | null) => void;
}

export function ResultsPanel({ scanned, activeFilter, scanRun, onFilterSelect }: Props) {
  function handleFilterSelect(kind: string | null) {
    onFilterSelect(kind);
  }

  return (
    <section className="panel panel--results" aria-label="분석 결과">
      <div className="panel__header">
        <div>
          <h2>
            <span aria-hidden="true">▱</span>
            분석 결과
          </h2>
        </div>
        {scanned && scanned.detections.length > 0 && (
          <span className="panel__badge">총 {scanned.detections.length}건 발견</span>
        )}
      </div>

      {scanned ? (
        <>
          <DetectionSummary
            detections={scanned.detections}
            activeFilter={activeFilter}
            onFilterSelect={handleFilterSelect}
          />
          <HighlightedText
            key={scanRun}
            text={scanned.text}
            detections={scanned.detections}
            activeFilter={activeFilter}
          />
        </>
      ) : (
        <div className="empty-state">
          <p>왼쪽에 텍스트를 입력하고 개인정보 탐지 및 마스킹을 실행하면 결과가 여기에 표시됩니다.</p>
        </div>
      )}
    </section>
  );
}
