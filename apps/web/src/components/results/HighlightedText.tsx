import { useEffect, useState } from "react";
import { buildSegments } from "../../lib/segments";
import { KIND_LABELS } from "../../types/detection";
import type { Detection } from "../../types/detection";

interface Props {
  text: string;
  detections: Detection[];
  activeFilter: string | null;
}

function classNames(...names: Array<string | false>) {
  return names.filter(Boolean).join(" ");
}

function isLowConfidence(detection: Detection) {
  return detection.confidence < 1;
}

function detectionKey(detection: Detection) {
  return `${detection.kind}:${detection.start}:${detection.end}`;
}

function maskText(text: string) {
  return "*".repeat(text.length);
}

const FILTER_REVEAL_MS = 6500;

export function HighlightedText({ text, detections, activeFilter }: Props) {
  const [coveredKeys, setCoveredKeys] = useState<Set<string>>(() => new Set());
  const [temporarilyRevealedKind, setTemporarilyRevealedKind] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const allCovered = detections.length > 0 && coveredKeys.size === detections.length;

  useEffect(() => {
    if (!activeFilter) {
      setTemporarilyRevealedKind(null);
      return;
    }

    setTemporarilyRevealedKind(activeFilter);
    const timeout = window.setTimeout(() => setTemporarilyRevealedKind(null), FILTER_REVEAL_MS);
    return () => window.clearTimeout(timeout);
  }, [activeFilter]);

  if (!text) {
    return <p className="highlighted-text highlighted-text--empty">텍스트를 입력하고 탐지를 실행해 주세요.</p>;
  }

  const segments = buildSegments(text, detections);
  // 복사·다운로드는 항상 이 완전 마스킹본만 내보낸다 — 개별 "가리기" 토글은 화면 데모용일 뿐,
  // 아무것도 안 가린 기본 상태에서 내보내면 원문이 그대로 유출되므로 토글 상태를 절대 참조하지 않는다(#104).
  const maskedText = segments.map((segment) => (segment.kind === "plain" ? segment.text : maskText(segment.text))).join("");

  function toggleCovered(key: string) {
    setCoveredKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function toggleCoverAll() {
    setCoveredKeys(allCovered ? new Set() : new Set(detections.map(detectionKey)));
  }

  async function copyMaskedResult() {
    await navigator.clipboard.writeText(maskedText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  function downloadMaskedResult() {
    const blob = new Blob([maskedText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "masked-result.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <div className="analysis-result" aria-label="분석 하이라이트 결과">
        <div className="analysis-result__toolbar">
          <p className="analysis-result__hint">! 원하는 테이프를 누르면 해당 개인정보가 가려집니다 !</p>
          <button
            type="button"
            className="analysis-result__cover-all"
            onClick={toggleCoverAll}
            disabled={detections.length === 0}
            aria-pressed={allCovered}
          >
            {allCovered ? "가리기 전으로" : "모두 가리기"}
          </button>
        </div>

        <div className="analysis-result__body">
          <p className="highlighted-text" data-testid="highlighted-text">
            {segments.map((segment, i) => {
              const isDetectionMatch = segment.kind !== "plain" && segment.detection.kind === activeFilter;
              const hasFilter = Boolean(activeFilter);
              const shouldDim = hasFilter && !isDetectionMatch;

              if (segment.kind === "plain") {
                return (
                  <span
                    key={i}
                    className={classNames(
                      "highlighted-text__plain",
                      shouldDim && "highlighted-text__plain--dimmed",
                    )}
                  >
                    {segment.text}
                  </span>
                );
              }

              const key = detectionKey(segment.detection);
              const isCovered = coveredKeys.has(key);
              const isTemporarilyRevealed = temporarilyRevealedKind === segment.detection.kind;
              const shouldFocus = hasFilter && isDetectionMatch;
              const label = KIND_LABELS[segment.detection.kind] ?? segment.detection.kind;

              return (
                <mark
                  key={i}
                  className={classNames(
                    "highlight",
                    "highlight--animated",
                    `highlight--${segment.detection.kind}`,
                    isLowConfidence(segment.detection) && "highlight--uncertain",
                    shouldFocus && "highlight--focused",
                    shouldDim && "highlight--dimmed",
                    isCovered && !isTemporarilyRevealed && "highlight--covered",
                    isCovered && isTemporarilyRevealed && "highlight--revealed",
                  )}
                  style={{ animationDelay: `${i * 40}ms` }}
                  title={`${label} · 신뢰도 ${Math.round(segment.detection.confidence * 100)}%`}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isCovered}
                  aria-label={`${label} ${isCovered ? "가림 해제" : "가리기"}`}
                  onClick={() => toggleCovered(key)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      toggleCovered(key);
                    }
                  }}
                >
                  {segment.text}
                  <span className="highlight__tag">{label}</span>
                </mark>
              );
            })}
          </p>

          <div className="analysis-result__export">
            <button
              type="button"
              className="analysis-result__copy"
              onClick={copyMaskedResult}
              aria-label={copied ? "마스킹 결과 복사됨" : "마스킹 결과 복사"}
              title={copied ? "복사됨" : "복사"}
            >
              <span className="copy-icon" aria-hidden="true" />
              <span>마스킹 결과 복사</span>
            </button>
            <button
              type="button"
              className="analysis-result__copy"
              onClick={downloadMaskedResult}
              aria-label="마스킹 결과 다운로드 (.txt)"
              title="다운로드"
            >
              <span aria-hidden="true">⬇</span>
              <span>다운로드</span>
            </button>
          </div>
          {copied && (
            <span className="analysis-result__copy-toast" role="status">
              복사되었습니다
            </span>
          )}
        </div>
      </div>
      <span className="masked-result__text" data-testid="masked-result">{maskedText}</span>
    </>
  );
}
