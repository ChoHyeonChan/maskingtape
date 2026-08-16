import { useEffect, useState } from "react";
import { DetectionSummary } from "./DetectionSummary";
import { HighlightedText } from "./HighlightedText";
import type { MaskMode } from "../../lib/masking";
import type { Detection } from "../../types/detection";

interface Props {
  scanned: { text: string; detections: Detection[] } | null;
  activeFilter: string | null;
  scanRun: number;
  maskMode?: MaskMode;
  onFilterSelect: (kind: string | null) => void;
}

const CONFIDENCE_STEP = 5;

export function ResultsPanel({ scanned, activeFilter, scanRun, maskMode = "mask", onFilterSelect }: Props) {
  // 새 탐지 결과가 나올 때마다 항상 안전한 기본값(0% = 전부 마스킹)으로 되돌아간다 —
  // 이전 탐지에서 올려둔 임계값이 새 텍스트에도 그대로 적용되면 검토 없이 과소 마스킹될 수 있다(#237).
  const [confidenceThreshold, setConfidenceThreshold] = useState(0);

  useEffect(() => {
    setConfidenceThreshold(0);
  }, [scanRun]);

  function handleFilterSelect(kind: string | null) {
    onFilterSelect(kind);
  }

  const allDetections = scanned?.detections ?? [];
  const visibleDetections = allDetections.filter(
    (detection) => detection.confidence * 100 >= confidenceThreshold,
  );
  const hiddenCount = allDetections.length - visibleDetections.length;

  // 필터 중인 종류가 확신도 임계값 때문에 화면에서 완전히 사라지면, 그 카드를 다시 눌러
  // 끌 방법이 없어 필터가 고정돼 버린다 — 남은 결과가 전부 흐려진 채로 갇히지 않도록
  // 자동으로 필터를 해제한다(#250).
  const activeFilterStillVisible =
    !activeFilter || visibleDetections.some((detection) => detection.kind === activeFilter);

  useEffect(() => {
    if (!activeFilterStillVisible) {
      onFilterSelect(null);
    }
  }, [activeFilterStillVisible, onFilterSelect]);

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
          {allDetections.length > 0 && (
            <div className="confidence-filter">
              <label htmlFor="confidence-threshold">
                확신도 <strong>{confidenceThreshold}%</strong> 이상만 마스킹
              </label>
              <input
                id="confidence-threshold"
                type="range"
                min={0}
                max={100}
                step={CONFIDENCE_STEP}
                value={confidenceThreshold}
                onChange={(event) => setConfidenceThreshold(Number(event.target.value))}
              />
              {hiddenCount > 0 && (
                <p className="confidence-filter__warning" role="status">
                  ⚠ {hiddenCount}건은 마스킹되지 않고 원문 그대로 표시됩니다.
                </p>
              )}
            </div>
          )}
          <DetectionSummary
            detections={visibleDetections}
            activeFilter={activeFilter}
            onFilterSelect={handleFilterSelect}
            hiddenByThreshold={allDetections.length > 0 && visibleDetections.length === 0}
          />
          <HighlightedText
            key={scanRun}
            text={scanned.text}
            detections={visibleDetections}
            activeFilter={activeFilter}
            maskMode={maskMode}
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
