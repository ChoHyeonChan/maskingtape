import { useEffect, useState } from "react";
import { scanText } from "../../api/scanClient";
import type { Detection } from "../../types/detection";

const PLACEHOLDER = "예: 고객 홍길동님은 010-1234-5678 또는 hong@example.com으로 연락 가능합니다.";
const MAX_TEXT_LENGTH = 100_000;

const PRESETS: { label: string; text: string }[] = [
  {
    label: "고객 상담 기록",
    text: "마스킹테이프 도입 검토 고객인 홍길동님과 전화 상담을 진행했습니다. 연락처는 010-1234-5678 또는 hong@example.com이며, 테스트 문서에는 주민등록번호 800101-1234560과 배송지 서울특별시 강남구 테헤란로 123이 함께 포함되어 있었습니다.",
  },
  {
    label: "신청서 샘플",
    text: "신청자 김민수, 주민등록번호 800101-1234560, 주소 서울특별시 강남구 테헤란로 123, 카드번호 4111-1111-1111-1111",
  },
  {
    label: "근로계약서 발췌",
    text: "근로계약서(발췌)\n사용자(갑): 마스킹테이프 주식회사\n근로자(을) 성명 김소연님, 주민등록번호 950322-2345671\n주소: 서울특별시 마포구 월드컵로 120 101동 502호\n연락처: 010-9876-5432\n위 당사자는 다음과 같이 근로계약을 체결하며, 근무 개시일은 2026년 3월 1일로 한다.",
  },
  {
    label: "임대차계약서 발췌",
    text: "주택임대차계약서(발췌)\n임차인 성명 박지훈씨, 주민등록번호 880715-1234567\n연락처 010-2345-6789, 이메일 jihoon.park@example.com\n주소: 경기도 성남시 분당구 정자동 178-4 스카이빌라 302동 1104호\n임대인과 위와 같이 전세 계약을 체결하며, 계약기간은 2026년 4월 1일부터 2028년 3월 31일까지로 한다.",
  },
];

interface Props {
  text: string;
  hasResult: boolean;
  resultVersion: number;
  onTextChange: (text: string) => void;
  onClear: () => void;
  onResult: (text: string, detections: Detection[]) => void;
}

export function InputPanel({ text, hasResult, resultVersion, onTextChange, onClear, onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [presetsOpen, setPresetsOpen] = useState(false);
  const [revealingResult, setRevealingResult] = useState(false);
  const trimmedLength = text.trim().length;
  const isTooLong = text.length > MAX_TEXT_LENGTH;
  const canScan = trimmedLength > 0 && !isTooLong;

  useEffect(() => {
    if (!hasResult || resultVersion === 0) return;

    setRevealingResult(true);
    const timeout = window.setTimeout(() => setRevealingResult(false), 950);
    return () => window.clearTimeout(timeout);
  }, [hasResult, resultVersion]);

  async function handleScan() {
    if (hasResult) {
      handleClear();
      return;
    }
    if (!canScan) return;
    setLoading(true);
    setError(null);
    try {
      const { detections } = await scanText(text);
      onResult(text, detections);
    } catch (err) {
      setError(err instanceof Error ? err.message : "탐지 요청 중 알 수 없는 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function handlePreset(text: string) {
    onTextChange(text);
    setError(null);
    setCopied(false);
    setPresetsOpen(false);
  }

  function handleClear() {
    onClear();
    setError(null);
    setCopied(false);
  }

  async function handleCopy() {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <div className="input-panel">
      <div className="input-panel__header">
        <h2><span aria-hidden="true">▤</span> {hasResult ? "탐지 결과" : "문서 입력"}</h2>
        <div className="input-panel__tools">
          <details
            className="input-panel__presets"
            data-coach="presets"
            open={presetsOpen}
            onToggle={(event) => setPresetsOpen(event.currentTarget.open)}
          >
            <summary className="input-panel__presets-label">예제 불러오기</summary>
            <div className="input-panel__preset-list">
              {PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="input-panel__preset"
                  onClick={() => handlePreset(preset.text)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </details>
          <button type="button" className="input-panel__sample" onClick={() => handlePreset(PRESETS[1].text)}>
            신청서 샘플
          </button>
        </div>
      </div>

      <div className={`input-panel__textarea-wrap${revealingResult ? " is-revealing" : ""}`}>
        {hasResult && (
          <>
            <button
              type="button"
              className="input-panel__copy-inline"
              onClick={handleCopy}
              disabled={!text}
              aria-label={copied ? "복사됨" : "마스킹 결과 복사"}
              title={copied ? "복사됨" : "복사"}
            >
              <span className="copy-icon" aria-hidden="true" />
            </button>
            {copied && (
              <span className="input-panel__copy-toast" role="status">
                복사되었습니다
              </span>
            )}
          </>
        )}
        <textarea
          className={revealingResult ? "is-text-revealing" : undefined}
          value={text}
          onChange={(event) => {
            onTextChange(event.target.value);
            if (error) setError(null);
            if (copied) setCopied(false);
          }}
          placeholder={PLACEHOLDER}
          rows={8}
          aria-label={hasResult ? "마스킹된 탐지 결과" : "탐지할 텍스트 입력"}
          aria-describedby="input-meta"
        />
        {revealingResult && (
          <pre className="input-panel__result-reveal" aria-hidden="true">
            {text}
          </pre>
        )}
      </div>

      <div className="input-panel__meta" id="input-meta">
        <span>{text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}자</span>
        {isTooLong && <span className="input-panel__limit">입력 길이를 줄여주세요.</span>}
      </div>

      <div className="input-panel__actions">
        <button
          type="button"
          onClick={handleScan}
          disabled={loading || (!canScan && !hasResult)}
          data-coach="scan"
          className={`input-panel__primary${canScan && !loading && !hasResult ? " is-ready" : " is-static"}`}
        >
          <span aria-hidden="true">{hasResult ? "↻" : "⌕"}</span>
          {hasResult ? "초기화 하기" : loading ? "처리 중..." : canScan ? "개인정보 탐지 및 마스킹 하기" : "텍스트 입력 필요"}
        </button>
        {!hasResult && (
          <button type="button" className="input-panel__secondary" onClick={handleClear} disabled={!text && !error}>
            <span aria-hidden="true">↻</span>
            초기화
          </button>
        )}
      </div>

      {error && (
        <p className="input-panel__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
