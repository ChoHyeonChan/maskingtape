import { buildSegments } from "../lib/segments";
import { KIND_LABELS } from "../types/detection";
import type { Detection } from "../types/detection";

interface Props {
  text: string;
  detections: Detection[];
}

export function HighlightedText({ text, detections }: Props) {
  if (!text) {
    return <p className="highlighted-text highlighted-text--empty">텍스트를 입력하고 탐지를 실행하세요.</p>;
  }

  const segments = buildSegments(text, detections);

  return (
    <p className="highlighted-text" data-testid="highlighted-text">
      {segments.map((segment, i) =>
        segment.kind === "plain" ? (
          <span key={i}>{segment.text}</span>
        ) : (
          <mark
            key={i}
            className={
              `highlight highlight--${segment.detection.kind}` +
              // 확신도 1.0 미만은 점선으로 "불확실" 표시 (이름·주소 등 규칙만으론 애매한 탐지)
              (segment.detection.confidence < 1 ? " highlight--uncertain" : "")
            }
            title={`${KIND_LABELS[segment.detection.kind] ?? segment.detection.kind} · 확신도 ${Math.round(
              segment.detection.confidence * 100,
            )}%`}
          >
            {segment.text}
            <span className="highlight__tag">{KIND_LABELS[segment.detection.kind] ?? segment.detection.kind}</span>
          </mark>
        ),
      )}
    </p>
  );
}
