import { useEffect, useState } from "react";

interface Props {
  onHelpClick: () => void;
}

const ACCURACY_BUBBLE_TIMEOUT_MS = 30_000;

export function AppHeader({ onHelpClick }: Props) {
  // 정확도 안내(예전엔 맨 아래 footer에만 있었다)를 도움말 버튼 옆에도 잠깐 띄워서, 처음
  // 쓰는 사람이 스크롤해서 맨 아래까지 안 내려도 "규칙 기반이라 이름을 놓칠 수 있다"는 걸
  // 바로 알게 한다. 30초 뒤 자동으로 사라지거나, 아무 데나 누르면 바로 닫힌다.
  const [showAccuracyBubble, setShowAccuracyBubble] = useState(true);

  useEffect(() => {
    if (!showAccuracyBubble) return;

    const timeout = window.setTimeout(() => setShowAccuracyBubble(false), ACCURACY_BUBBLE_TIMEOUT_MS);
    function dismiss() {
      setShowAccuracyBubble(false);
    }
    window.addEventListener("click", dismiss);
    return () => {
      window.clearTimeout(timeout);
      window.removeEventListener("click", dismiss);
    };
  }, [showAccuracyBubble]);

  return (
    <header className="app-header">
      <div className="app-header__content">
        <img
          className="brand-logo"
          src="/maskingtape-logo-blue.png"
          alt="MaskingTape"
          width={1501}
          height={276}
        />
        <p>한국어 문서 속 개인정보를 탐지하고, 안전하게 마스킹해 공유할 수 있게 돕습니다.</p>
      </div>

      <button
        type="button"
        className="help-button"
        aria-label="사용 안내 다시 보기"
        data-tooltip="도움말"
        onClick={onHelpClick}
      >
        i
      </button>

      {showAccuracyBubble && (
        <div className="accuracy-bubble" role="status">
          <p>
            이 웹 데모는 <strong>규칙 기반 탐지만</strong> 사용합니다. 문맥 단서가 없는 이름 일부는
            놓칠 수 있어요 — 로컬 설치 후 <code>--llm</code> 옵션을 쓰면 로컬 LLM으로 이름까지 더
            정확하게 탐지합니다.
          </p>
          <span className="accuracy-bubble__dismiss-hint">아무 데나 누르면 닫힙니다</span>
        </div>
      )}
    </header>
  );
}
