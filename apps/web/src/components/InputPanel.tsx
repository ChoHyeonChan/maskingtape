import { useState } from "react";
import { scanText } from "../api/scanClient";
import type { Detection } from "../types/detection";

const PLACEHOLDER = "예: 고객 홍길동님 010-1234-5678로 연락 부탁드립니다. 서울특별시 강남구 역삼동 123-4";

// 데모용 합성 예제 — 모든 번호·주민번호는 체크섬만 맞춘 가짜다(§실격 규정: 진짜 개인정보 금지).
const PRESETS: { label: string; text: string }[] = [
  {
    label: "상담 메모",
    text: "고객 홍길동님께 010-1234-5678로 안내드렸고, 이메일 hong@example.com도 보냈습니다.",
  },
  {
    label: "신청서",
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

  async function handleScan() {
    if (!text.trim()) return;
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

  return (
    <div className="input-panel">
      <div className="input-panel__presets">
        <span className="input-panel__presets-label">예제:</span>
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
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={PLACEHOLDER}
        rows={6}
        aria-label="탐지할 텍스트 입력"
      />
      <div className="input-panel__actions">
        <button onClick={handleScan} disabled={loading || !text.trim()}>
          {loading ? "탐지 중..." : "개인정보 탐지"}
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
