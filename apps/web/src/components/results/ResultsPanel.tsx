import { useEffect, useRef, useState } from "react";
import { DetectionList } from "./DetectionList";
import type { DetectionRow } from "./DetectionList";
import { applyMasking, type MaskMode } from "../../lib/masking";
import type { Detection } from "../../types/detection";

interface Props {
  scanned: { text: string; detections: Detection[] } | null;
  scanRun: number;
  maskMode?: MaskMode;
  onMaskedTextChange: (text: string) => void;
}

const THRESHOLD_STEP = 5;
const MIN_THRESHOLD = 0;
const MAX_THRESHOLD = 100;
// 탐지 결과가 없을 때(이론상 도달 안 함 — 있으면 리스트 자체를 안 그린다)를 위한 안전값.
const FALLBACK_THRESHOLD = 50;

function detectionKey(detection: Detection) {
  return `${detection.kind}:${detection.start}:${detection.end}`;
}

/** 화면에 보이는 "N%"와 항상 같은 기준으로 비교하도록, 확신도도 표시와 동일하게 반올림한다. */
function confidencePercent(detection: Detection): number {
  return Math.round(detection.confidence * 100);
}

export function ResultsPanel({ scanned, scanRun, maskMode = "mask", onMaskedTextChange }: Props) {
  // 컨트롤에 보이는 숫자가 곧 확신도 임계값이다(더 이상 반전 없음) — 이 값 이상인 항목만
  // 기본으로 가려진다. 고정값(예: 50%) 대신 이번 스캔에서 가장 낮은 확신도로 시작하면,
  // 처음부터 "전부 가려짐" 상태에서 슬라이더를 올릴 때마다 확신도 낮은 항목부터 바로바로
  // 반응이 보여 조절 범위가 낭비되지 않는다.
  const [confidenceThreshold, setConfidenceThreshold] = useState(FALLBACK_THRESHOLD);
  // 항목별 수동 override — 일괄 조정(확신도 임계값)보다 우선한다. 스캔이 바뀌면 초기화된다.
  const [overrides, setOverrides] = useState<Map<string, boolean>>(() => new Map());
  const resultsRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const confidences = (scanned?.detections ?? []).map(confidencePercent);
    setConfidenceThreshold(confidences.length > 0 ? Math.min(...confidences) : FALLBACK_THRESHOLD);
    setOverrides(new Map());
    // scanned는 scanRun과 함께(같은 이벤트 안에서) 갱신되므로, scanRun만으로 "새 스캔마다"를
    // 판단해도 이 시점엔 이미 최신 scanned를 읽는다 — 아래 스크롤 이펙트와 동일한 전제.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanRun]);

  // 모바일 단일 컬럼 레이아웃에서는 결과가 뷰포트 아래에 생겨, 스캔 버튼을 눌러도 화면에
  // 아무 변화가 안 보여 "반응이 없다"로 오해하기 쉽다 — 결과로 스크롤·포커스를 옮겨 확실히
  // 알려준다(#308). scanRun이 0(아직 스캔 전)일 때는 건너뛴다.
  useEffect(() => {
    if (scanRun === 0) return;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    resultsRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" });
    resultsRef.current?.focus();
  }, [scanRun]);

  const allDetections = scanned?.detections ?? [];
  const sorted = [...allDetections].sort((a, b) => a.start - b.start);

  function isMasked(detection: Detection): boolean {
    const key = detectionKey(detection);
    const override = overrides.get(key);
    if (override !== undefined) return override;
    return confidencePercent(detection) >= confidenceThreshold;
  }

  const rows: DetectionRow[] = sorted.map((detection) => ({
    detection,
    key: detectionKey(detection),
    snippet: scanned ? scanned.text.slice(detection.start, detection.end) : "",
    masked: isMasked(detection),
  }));

  const maskedDetections = rows.filter((row) => row.masked).map((row) => row.detection);
  const maskedText = scanned ? applyMasking(scanned.text, maskedDetections, maskMode) : "";

  useEffect(() => {
    onMaskedTextChange(maskedText);
  }, [maskedText, onMaskedTextChange]);

  function handleToggle(detection: Detection) {
    const key = detectionKey(detection);
    setOverrides((current) => {
      const next = new Map(current);
      next.set(key, !isMasked(detection));
      return next;
    });
  }

  return (
    <section className="panel panel--results" aria-label="탐지 결과 조정" ref={resultsRef} tabIndex={-1}>
      <div className="panel__header">
        <div>
          <h2 data-coach="analysis-result">
            <span aria-hidden="true">▱</span>
            탐지 결과 조정
          </h2>
        </div>
        {scanned && scanned.detections.length > 0 && (
          <span className="panel__badge">총 {scanned.detections.length}건 발견</span>
        )}
      </div>

      {scanned ? (
        <DetectionList
          rows={rows}
          confidenceThreshold={confidenceThreshold}
          minThreshold={MIN_THRESHOLD}
          maxThreshold={MAX_THRESHOLD}
          thresholdStep={THRESHOLD_STEP}
          onThresholdChange={setConfidenceThreshold}
          onToggle={handleToggle}
        />
      ) : (
        <div className="empty-state">
          <p>왼쪽에 텍스트를 입력하고 개인정보 탐지 및 마스킹을 실행하면 결과가 여기에 표시됩니다.</p>
        </div>
      )}
    </section>
  );
}
