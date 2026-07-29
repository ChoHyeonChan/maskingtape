import { useLayoutEffect, useRef, useState } from "react";
import { scanText } from "../../api/scanClient";
import type { Detection } from "../../types/detection";

const PLACEHOLDER = "예: 고객 홍길동님은 010-1234-5678 또는 hong@example.com으로 연락 가능합니다.";
const MAX_TEXT_LENGTH = 100_000;
const TEXTAREA_BOTTOM_MARGIN = 118;
const TEXTAREA_MIN_HEIGHT = 260;

const PRESETS: { label: string; text: string }[] = [
  {
    label: "고객 상담 기록",
    text: "마스킹테이프 도입 검토 고객인 홍길동님과 전화 상담을 진행했습니다. 연락처는 010-1234-5678 또는 hong@example.com이며, 테스트 문서에는 주민등록번호 800101-1234560과 배송지 서울특별시 강남구 테헤란로 123이 함께 포함되어 있었습니다.",
  },
  {
    label: "신청서 샘플",
    text: "신청자 김민수, 주민등록번호 800101-1234560, 주소 서울특별시 강남구 테헤란로 123, 카드번호 4111-1111-1111-1111",
  },
];

interface Props {
  onResult: (text: string, detections: Detection[]) => void;
}

export function InputPanel({ onResult }: Props) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const trimmedLength = text.trim().length;
  const isTooLong = text.length > MAX_TEXT_LENGTH;
  const canScan = trimmedLength > 0 && !isTooLong;

  useLayoutEffect(() => {
    function resizeTextarea() {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const top = textarea.getBoundingClientRect().top;
      const maxHeight = Math.max(TEXTAREA_MIN_HEIGHT, window.innerHeight - top - TEXTAREA_BOTTOM_MARGIN);
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(maxHeight, textarea.scrollHeight)}px`;
      textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
    }

    resizeTextarea();
    window.addEventListener("resize", resizeTextarea);
    return () => window.removeEventListener("resize", resizeTextarea);
  }, [text]);

  async function handleScan() {
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
    setText(text);
    setError(null);
  }

  function handleClear() {
    setText("");
    setError(null);
  }

  return (
    <div className="input-panel">
      <div className="input-panel__presets" data-coach="presets">
        <span className="input-panel__presets-label">예제</span>
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

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          if (error) setError(null);
        }}
        placeholder={PLACEHOLDER}
        rows={8}
        aria-label="탐지할 텍스트 입력"
        aria-describedby="input-meta"
      />

      <div className="input-panel__meta" id="input-meta">
        <span>{text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}자</span>
        {isTooLong && <span className="input-panel__limit">입력 길이를 줄여주세요.</span>}
      </div>

      <div className="input-panel__actions">
        <button
          type="button"
          onClick={handleScan}
          disabled={loading || !canScan}
          data-coach="scan"
          className={`input-panel__primary${canScan && !loading ? " is-ready" : " is-idle"}`}
        >
          {loading ? "탐지 중..." : canScan ? "개인정보 탐지" : "텍스트 입력 필요"}
        </button>
        <button type="button" className="input-panel__secondary" onClick={handleClear} disabled={!text && !error}>
          지우기
        </button>
      </div>

      {error && (
        <p className="input-panel__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
