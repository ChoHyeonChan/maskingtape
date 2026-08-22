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

const STRENGTH_STEP = 5;
const MAX_STRENGTH = 100;

function detectionKey(detection: Detection) {
  return `${detection.kind}:${detection.start}:${detection.end}`;
}

export function ResultsPanel({ scanned, scanRun, maskMode = "mask", onMaskedTextChange }: Props) {
  // 슬라이더 오른쪽 끝(최댓값)이 "전부 마스킹"이 되도록 확신도가 아니라 마스킹 강도로 값을 다룬다 —
  // "오른쪽=더 강하게 보호"라는 직관과 "덜 가리기=유출"이라는 보안 원칙이 둘 다 오른쪽=안전으로
  // 일치해야 실수로 조작해도 위험한 방향(노출)이 아니라 안전한 방향으로 치우친다(#264).
  // 새 탐지 결과가 나올 때마다 항상 최댓값(전부 마스킹)으로 되돌아간다(#237 회귀 없음).
  const [maskingStrength, setMaskingStrength] = useState(MAX_STRENGTH);
  // 항목별 수동 override — 일괄 조정(확신도 임계값)보다 우선한다. 스캔이 바뀌면 초기화된다.
  const [overrides, setOverrides] = useState<Map<string, boolean>>(() => new Map());
  const resultsRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setMaskingStrength(MAX_STRENGTH);
    setOverrides(new Map());
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

  // 강도가 낮아질수록 더 높은 확신도인 항목만 기본으로 가려진다.
  const confidenceThreshold = MAX_STRENGTH - maskingStrength;

  const allDetections = scanned?.detections ?? [];
  const sorted = [...allDetections].sort((a, b) => a.start - b.start);

  function isMasked(detection: Detection): boolean {
    const key = detectionKey(detection);
    const override = overrides.get(key);
    if (override !== undefined) return override;
    return detection.confidence * 100 >= confidenceThreshold;
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
          maskingStrength={maskingStrength}
          minStrength={0}
          maxStrength={MAX_STRENGTH}
          strengthStep={STRENGTH_STEP}
          onStrengthChange={setMaskingStrength}
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
