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
  const [copiedOriginal, setCopiedOriginal] = useState(false);
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
  const maskedText = segments.map((segment) => (segment.kind === "plain" ? segment.text : maskText(segment.text))).join("");
  const copyText = segments
    .map((segment) => {
      if (segment.kind === "plain") return segment.text;
      return coveredKeys.has(detectionKey(segment.detection)) ? maskText(segment.text) : segment.text;
    })
    .join("");

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

  async function copyOriginal() {
    await navigator.clipboard.writeText(copyText);
    setCopiedOriginal(true);
    window.setTimeout(() => setCopiedOriginal(false), 1400);
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
              const confidencePct = Math.round(segment.detection.confidence * 100);
              const uncertain = isLowConfidence(segment.detection);
              // 확신도는 hover 전용 title 툴팁만으론 키보드·터치 사용자에게 전달되지 않는다(#106).
              // 애매한(확신도<100%) 건만 태그에 %를 붙여 시각적으로도 드러내고, aria-label에는
              // 모든 건에 확신도를 넣어 스크린리더로도 항상 전달되게 한다.
              const tagText = uncertain ? `${label} · ${confidencePct}%` : label;

              return (
                <mark
                  key={i}
                  className={classNames(
                    "highlight",
                    "highlight--animated",
                    `highlight--${segment.detection.kind}`,
                    uncertain && "highlight--uncertain",
                    shouldFocus && "highlight--focused",
                    shouldDim && "highlight--dimmed",
                    isCovered && !isTemporarilyRevealed && "highlight--covered",
                    isCovered && isTemporarilyRevealed && "highlight--revealed",
                  )}
                  style={{ animationDelay: `${i * 40}ms` }}
                  title={`${label} · 신뢰도 ${confidencePct}%`}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isCovered}
                  aria-label={`${label} · 신뢰도 ${confidencePct}% · ${isCovered ? "가림 해제" : "가리기"}`}
                  onClick={() => toggleCovered(key)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      toggleCovered(key);
                    }
                  }}
                >
                  {segment.text}
                  <span className="highlight__tag">{tagText}</span>
                </mark>
              );
            })}
          </p>

          <button
            type="button"
            className="analysis-result__copy"
            onClick={copyOriginal}
            aria-label={copiedOriginal ? "분석 결과 복사됨" : "분석 결과 내용 복사"}
            title={copiedOriginal ? "복사됨" : "복사"}
          >
            <span className="copy-icon" aria-hidden="true" />
            <span>이대로 복사하기</span>
          </button>
          {copiedOriginal && (
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
