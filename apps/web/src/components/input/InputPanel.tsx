import { useLayoutEffect, useRef, useState } from "react";
import { scanText } from "../../api/scanClient";
import type { Detection } from "../../types/detection";

const PLACEHOLDER = "예: 고객 홍길동님 010-1234-5678로 연락 부탁드립니다. 서울특별시 강남구 역삼동 123-4";
const TEXTAREA_BOTTOM_MARGIN = 118;
const TEXTAREA_MIN_HEIGHT = 260;

// 데모용 합성 예제 — 모든 번호·주민번호는 체크섬만 맞춘 가짜다(§실격 규정: 진짜 개인정보 금지).
const PRESETS: { label: string; text: string }[] = [
  {
    label: "예제 1 · 고객 지원 기록",
    text: "마스킹테이프 도입 검토 고객인 홍길동님과 온보딩 상담을 진행했습니다. 회신은 010-1234-5678 또는 hong@example.com으로 요청받았고, 테스트 문서에는 주민등록번호 800101-1234560과 배송지 서울특별시 강남구 역삼동 123-4가 함께 포함되어 있었습니다. 외부 협업 도구에 공유하기 전 이름, 연락처, 이메일, 주민등록번호, 주소가 한 번에 탐지되고 가려지는지 확인이 필요합니다.",
  },
  {
    label: "예제 2 · 신청서",
    text: "신청자 김영희, 주민등록번호 800101-1234560, 주소 서울특별시 강남구 역삼동 123-4",
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

  const canScan = text.trim().length > 0;

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

  function handleClear() {
    setText("");
    setError(null);
  }

  return (
    <div className="input-panel">
      <div className="input-panel__presets" data-coach="presets">
        <span className="input-panel__presets-label">예제 선택</span>
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            type="button"
            className="input-panel__preset"
            onClick={() => setText(preset.text)}
          >
            {preset.label}
          </button>
        ))}
      </div>
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={PLACEHOLDER}
        rows={8}
        aria-label="탐지할 텍스트 입력"
      />
      <div className="input-panel__actions">
        <button
          onClick={handleScan}
          disabled={loading || !canScan}
          data-coach="scan"
          className={`input-panel__primary${canScan && !loading ? " is-ready" : " is-idle"}`}
        >
          {loading ? "탐지 중..." : canScan ? "탐지 결과 보기" : "텍스트를 입력해 주세요"}
        </button>
        <button type="button" className="input-panel__secondary" onClick={handleClear}>
          초기화
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
