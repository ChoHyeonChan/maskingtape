import { useState } from "react";
import { scanText } from "../api/scanClient";
import type { Detection } from "../types/detection";

const PLACEHOLDER = "예: 고객 홍길동님 010-1234-5678로 연락 부탁드립니다. 서울특별시 강남구 역삼동 123-4";

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
