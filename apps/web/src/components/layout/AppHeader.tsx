import { useEffect, useRef, useState } from "react";

interface Props {
  onHelpClick: () => void;
  hasResult?: boolean;
}

const ACCURACY_BUBBLE_TIMEOUT_MS = 30_000;

export function AppHeader({ onHelpClick, hasResult = false }: Props) {
  // 정확도 안내(예전엔 맨 아래 footer에만 있었다)를 도움말 버튼 옆에도 잠깐 띄워서, 처음
  // 쓰는 사람이 스크롤해서 맨 아래까지 안 내려도 "규칙 기반이라 이름을 놓칠 수 있다"는 걸
  // 바로 알게 한다. 예전엔 아무 데나 클릭해도 닫혔는데, 그러면 텍스트를 입력하거나 탐지
  // 결과를 보려고 클릭하는 순간 바로 사라져서 정작 결과 화면까지는 못 보고 닫혀버렸다 —
  // 이제는 30초 뒤 자동으로 사라지거나, 말풍선의 X 버튼을 눌러야만 닫힌다.
  const [showAccuracyBubble, setShowAccuracyBubble] = useState(true);
  const wasResult = useRef(false);

  useEffect(() => {
    if (!showAccuracyBubble) return;

    const timeout = window.setTimeout(() => setShowAccuracyBubble(false), ACCURACY_BUBBLE_TIMEOUT_MS);
    return () => window.clearTimeout(timeout);
  }, [showAccuracyBubble]);

  // 처음 페이지에서 30초 안에 못 보고 지나쳤다면, 정작 결과를 확인하는 시점(놓친 이름이
  // 있을까 궁금해질 때)엔 이미 사라져 있었다 — 탐지 결과가 막 나온 순간에도 다시 띄워준다.
  useEffect(() => {
    if (hasResult && !wasResult.current) {
      setShowAccuracyBubble(true);
    }
    wasResult.current = hasResult;
  }, [hasResult]);

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

      <div className="help-button-wrap">
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
            <button
              type="button"
              className="accuracy-bubble__close"
              aria-label="정확도 안내 닫기"
              onClick={() => setShowAccuracyBubble(false)}
            >
              ×
            </button>
            <p>
              규칙 기반 탐지라 이름 일부를 놓칠 수 있어요 — <strong>정확한 결과가 필요하면 로컬 설치를
              권장합니다.</strong>
            </p>
          </div>
        )}
      </div>
    </header>
  );
}
