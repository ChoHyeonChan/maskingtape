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
  return (
    <section className="panel panel--results" aria-label="탐지 결과">
      <div className="panel__header">
        <div>
          <p className="eyebrow">실시간 결과</p>
          <h2>탐지 결과</h2>
        </div>
      </div>

      {scanned ? (
        <>
          <DetectionSummary
            detections={scanned.detections}
            activeFilter={activeFilter}
            onFilterSelect={onFilterSelect}
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
          <p>텍스트를 입력하고 탐지 결과 보기를 누르면 이곳에 표시됩니다.</p>
        </div>
      )}
    </section>
  );
}
