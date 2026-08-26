import { useEffect, useRef, useState } from "react";
import { DetectionList } from "./DetectionList";
import type { DetectionRow } from "./DetectionList";
import { anonymizeText } from "../../api/scanClient";
import { locateDetections, type MaskMode } from "../../lib/masking";
import { KIND_COLORS } from "../../types/detection";
import type { Detection, HighlightRange } from "../../types/detection";

interface Props {
  scanned: { text: string; detections: Detection[] } | null;
  scanRun: number;
  maskMode?: MaskMode;
  onMaskedTextChange: (text: string) => void;
  onHighlightChange?: (highlight: HighlightRange | null) => void;
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

export function ResultsPanel({
  scanned,
  scanRun,
  maskMode = "mask",
  onMaskedTextChange,
  onHighlightChange = () => {},
}: Props) {
  // 컨트롤에 보이는 숫자가 곧 확신도 임계값이다(더 이상 반전 없음) — 이 값 이상인 항목만
  // 기본으로 가려진다. 고정값(예: 50%) 대신 이번 스캔에서 가장 낮은 확신도로 시작하면,
  // 처음부터 "전부 가려짐" 상태에서 슬라이더를 올릴 때마다 확신도 낮은 항목부터 바로바로
  // 반응이 보여 조절 범위가 낭비되지 않는다.
  const [confidenceThreshold, setConfidenceThreshold] = useState(FALLBACK_THRESHOLD);
  // 항목별 수동 override — 일괄 조정(확신도 임계값)보다 우선한다. 스캔이 바뀌면 초기화된다.
  const [overrides, setOverrides] = useState<Map<string, boolean>>(() => new Map());
  const resultsRef = useRef<HTMLElement>(null);

  // pseudonym(가명처리)은 core의 값 생성 로직이 필요해 mask/label처럼 클라이언트에서
  // 즉시 계산할 수 없다 — /anonymize를 호출해서 받는다(#346). 그동안은 로딩·에러 상태를
  // 따로 들고, 이 모드에서는 항목별 조정 목록(DetectionList) 대신 안내만 보여준다.
  const [pseudonymText, setPseudonymText] = useState<string | null>(null);
  const [pseudonymLoading, setPseudonymLoading] = useState(false);
  const [pseudonymError, setPseudonymError] = useState<string | null>(null);

  useEffect(() => {
    if (maskMode !== "pseudonym" || !scanned) {
      setPseudonymText(null);
      setPseudonymLoading(false);
      setPseudonymError(null);
      return;
    }

    // 이 모드엔 항목별 가림/노출 조정이 없으니, 오른쪽 목록 호버로 남아있을 수 있는
    // 왼쪽 강조를 지워 상태가 어긋나 보이지 않게 한다.
    onHighlightChange(null);

    let ignore = false;
    setPseudonymLoading(true);
    setPseudonymError(null);

    anonymizeText(scanned.text, "pseudonym")
      .then((result) => {
        if (ignore) return;
        setPseudonymText(result.text);
      })
      .catch((err) => {
        if (ignore) return;
        setPseudonymError(err instanceof Error ? err.message : "가명처리 요청 중 알 수 없는 오류가 발생했습니다.");
      })
      .finally(() => {
        if (!ignore) setPseudonymLoading(false);
      });

    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maskMode, scanned]);

  useEffect(() => {
    const confidences = (scanned?.detections ?? []).map(confidencePercent);
    setConfidenceThreshold(confidences.length > 0 ? Math.min(...confidences) : FALLBACK_THRESHOLD);
    setOverrides(new Map());
    onHighlightChange(null);
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

  const { text: maskedText, ranges } =
    scanned && maskMode !== "pseudonym"
      ? locateDetections(scanned.text, rows, maskMode)
      : { text: "", ranges: new Map<string, [number, number]>() };

  const displayedText = maskMode === "pseudonym" ? (pseudonymText ?? "") : maskedText;

  useEffect(() => {
    onMaskedTextChange(displayedText);
  }, [displayedText, onMaskedTextChange]);

  // "일괄 조정"은 이름 그대로 전체를 다시 정하는 컨트롤이다 — 이전에 항목 몇 개를 수동으로
  // 뒤집어(override) 둔 상태에서 이 슬라이더/링을 만지면, override가 남아있는 항목은 새
  // 값을 무시하고 그대로 있어서 "숫자를 바꿔도 안 먹힌다"는 인상을 줬다. 일괄 조정을
  // 만지는 순간 그 의도(전체 재적용)를 살려 개별 override를 전부 지운다.
  function handleThresholdChange(next: number) {
    setConfidenceThreshold(next);
    setOverrides(new Map());
  }

  function handleToggle(detection: Detection) {
    const key = detectionKey(detection);
    setOverrides((current) => {
      const next = new Map(current);
      next.set(key, !isMasked(detection));
      return next;
    });
  }

  // 항목에 마우스를 올리면 왼쪽 "마스킹 결과" 텍스트에서 그 항목이 실제로 자리한 부분을
  // 강조한다 — 두 패널이 화면에서 멀리 떨어져 있어, 항목별 조정이 왼쪽 어디에 해당하는지
  // 한눈에 잇기 어렵다는 피드백에 대응한다.
  function handleRowHover(key: string | null) {
    if (key === null) {
      onHighlightChange(null);
      return;
    }
    const range = ranges.get(key);
    const row = rows.find((candidate) => candidate.key === key);
    if (!range || !row) {
      onHighlightChange(null);
      return;
    }
    onHighlightChange({
      start: range[0],
      end: range[1],
      color: KIND_COLORS[row.detection.kind] ?? "var(--kind-fallback)",
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

      {scanned && maskMode === "pseudonym" ? (
        <div className="pseudonym-panel">
          <p className="pseudonym-note">
            가명처리는 같은 원본값을 항상 같은 그럴듯한 가짜 값으로 바꿔 문서의 구조와 맥락을
            그대로 유지합니다. 이 모드에서는 항목별 가림·노출 조정을 지원하지 않습니다.
          </p>
          {pseudonymLoading && (
            <p className="pseudonym-status" role="status">
              가명처리 결과를 불러오는 중...
            </p>
          )}
          {pseudonymError && (
            <p className="pseudonym-status pseudonym-status--error" role="alert">
              {pseudonymError}
            </p>
          )}
          {!pseudonymLoading && !pseudonymError && scanned.detections.length === 0 && (
            <p className="detect-empty" role="status">
              개인정보가 발견되지 않았습니다.
            </p>
          )}
        </div>
      ) : scanned ? (
        <DetectionList
          rows={rows}
          confidenceThreshold={confidenceThreshold}
          minThreshold={MIN_THRESHOLD}
          maxThreshold={MAX_THRESHOLD}
          thresholdStep={THRESHOLD_STEP}
          onThresholdChange={handleThresholdChange}
          onToggle={handleToggle}
          onRowHover={handleRowHover}
        />
      ) : (
        <div className="empty-state">
          <p>왼쪽에 텍스트를 입력하고 개인정보 탐지 및 마스킹을 실행하면 결과가 여기에 표시됩니다.</p>
        </div>
      )}
    </section>
  );
}
