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

const FILTER_REVEAL_MS = 6500;

export function HighlightedText({ text, detections, activeFilter }: Props) {
  const [coveredKeys, setCoveredKeys] = useState<Set<string>>(() => new Set());
  const [temporarilyRevealedKind, setTemporarilyRevealedKind] = useState<string | null>(null);
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
    return <p className="highlighted-text highlighted-text--empty">텍스트를 입력하고 탐지를 실행하세요.</p>;
  }

  const segments = buildSegments(text, detections);

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

  return (
    <>
      <p className="highlighted-text__hint">👇 개인정보를 클릭하면 마스킹테이프로 가려져요.</p>
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
              title={`${label} · 확신도 ${Math.round(segment.detection.confidence * 100)}%`}
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
      <div className="result-actions">
        
        <button
          type="button"
          className="result-actions__button"
          onClick={toggleCoverAll}
          disabled={detections.length === 0}
          aria-pressed={allCovered}
        >
          {allCovered ? "가리기 전으로" : "모두 가리기"}
        </button>
      </div>
    </>
  );
}
