import { useEffect, useState } from "react";
import { DetectionSummary } from "./DetectionSummary";
import { HighlightedText } from "./HighlightedText";
import type { Detection } from "../../types/detection";

interface Props {
  scanned: { text: string; detections: Detection[] } | null;
  activeFilter: string | null;
  scanRun: number;
  onFilterSelect: (kind: string | null) => void;
}

const STRENGTH_STEP = 5;
const MAX_STRENGTH = 100;

export function ResultsPanel({ scanned, activeFilter, scanRun, onFilterSelect }: Props) {
  // 슬라이더 오른쪽 끝(최댓값)이 "전부 마스킹"이 되도록 확신도가 아니라 마스킹 강도로 값을 다룬다 —
  // "오른쪽=더 강하게 보호"라는 직관과 "덜 가리기=유출"이라는 보안 원칙이 둘 다 오른쪽=안전으로
  // 일치해야 실수로 슬라이더를 조작해도 위험한 방향(노출)이 아니라 안전한 방향으로 치우친다(#264).
  // 새 탐지 결과가 나올 때마다 항상 최댓값(전부 마스킹)으로 되돌아간다(#237 회귀 없음).
  const [maskingStrength, setMaskingStrength] = useState(MAX_STRENGTH);

  useEffect(() => {
    setMaskingStrength(MAX_STRENGTH);
  }, [scanRun]);

  function handleFilterSelect(kind: string | null) {
    onFilterSelect(kind);
  }

  // 강도가 낮아질수록(왼쪽으로 갈수록) 더 높은 확신도인 항목만 마스킹 대상으로 남는다.
  const confidenceThreshold = MAX_STRENGTH - maskingStrength;

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
                마스킹 강도 <strong>{maskingStrength}%</strong>
                <span className="confidence-filter__sublabel">
                  (확신도 {confidenceThreshold}% 이상만 가립니다)
                </span>
              </label>
              <input
                id="confidence-threshold"
                type="range"
                min={0}
                max={MAX_STRENGTH}
                step={STRENGTH_STEP}
                value={maskingStrength}
                onChange={(event) => setMaskingStrength(Number(event.target.value))}
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
