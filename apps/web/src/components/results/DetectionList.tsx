import { useState } from "react";
import { ConfidenceControl } from "./ConfidenceControl";
import { KIND_COLORS, KIND_LABELS } from "../../types/detection";
import type { Detection } from "../../types/detection";

export interface DetectionRow {
  detection: Detection;
  key: string;
  snippet: string;
  masked: boolean;
}

interface Props {
  rows: DetectionRow[];
  maskingStrength: number;
  minStrength: number;
  maxStrength: number;
  strengthStep: number;
  confidenceThreshold: number;
  onStrengthChange: (next: number) => void;
  onToggle: (detection: Detection) => void;
  maskedText: string;
}

/**
 * 탐지된 개인정보를 항목 하나하나로 나열하고, 각 항목의 가림/보임을 실제로 제어한다.
 * (예전 카드 그리드는 필터 UI였을 뿐 실제 마스킹 결과에 영향이 없었다 — 이제 토글이 진짜로 반영된다.)
 */
export function DetectionList({
  rows,
  maskingStrength,
  minStrength,
  maxStrength,
  strengthStep,
  confidenceThreshold,
  onStrengthChange,
  onToggle,
  maskedText,
}: Props) {
  const [copied, setCopied] = useState(false);
  const maskedCount = rows.filter((row) => row.masked).length;
  const exposedCount = rows.length - maskedCount;

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

  if (rows.length === 0) {
    return (
      <p className="detect-empty" role="status">
        개인정보가 발견되지 않았습니다.
      </p>
    );
  }

  return (
    <div className="detect">
      <div className="detect__bulk">
        <div className="detect__bulk-head">
          <span className="detect__bulk-title">일괄 조정</span>
          <span className="detect__bulk-sublabel">확신도 {confidenceThreshold}% 이상은 기본으로 가립니다</span>
        </div>
        <ConfidenceControl
          value={maskingStrength}
          min={minStrength}
          max={maxStrength}
          step={strengthStep}
          onChange={onStrengthChange}
        />
      </div>

      <p className="detect__summary" role="status">
        개인정보 {rows.length}건 발견 · {maskedCount}건 가림 · {exposedCount}건 노출
      </p>

      <ul className="detect__list" aria-label="탐지된 개인정보 목록">
        {rows.map(({ detection, key, snippet, masked }) => {
          const label = KIND_LABELS[detection.kind] ?? detection.kind;
          const confidencePct = Math.round(detection.confidence * 100);
          return (
            <li key={key} className="detect-row">
              <span
                className="detect-row__dot"
                aria-hidden="true"
                style={{ background: KIND_COLORS[detection.kind] ?? "var(--kind-fallback)" }}
              />
              <span className="detect-row__kind">{label}</span>
              <span className="detect-row__snippet">{snippet}</span>
              <span className="detect-row__confidence">{confidencePct}%</span>
              <button
                type="button"
                role="switch"
                aria-checked={masked}
                aria-label={`${label} ${snippet} ${masked ? "가려짐 — 눌러서 보이게 하기" : "보임 — 눌러서 가리기"}`}
                className={`detect-row__toggle${masked ? " is-masked" : ""}`}
                onClick={() => onToggle(detection)}
              >
                {masked ? "가림" : "보임"}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="detect__export">
        <button
          type="button"
          className="detect__export-btn"
          onClick={copyMaskedResult}
          aria-label={copied ? "마스킹 결과 복사됨" : "마스킹 결과 복사"}
        >
          <span className="copy-icon" aria-hidden="true" />
          <span>마스킹 결과 복사</span>
        </button>
        <button type="button" className="detect__export-btn" onClick={downloadMaskedResult}>
          <span aria-hidden="true">⬇</span>
          <span>다운로드</span>
        </button>
        {copied && (
          <span className="detect__copy-toast" role="status">
            복사되었습니다
          </span>
        )}
      </div>
    </div>
  );
}
