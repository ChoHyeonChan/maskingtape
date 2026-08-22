import { useRef, useState } from "react";
import { CoachMark } from "./components/help/CoachMark";
import { InputPanel } from "./components/input/InputPanel";
import { AppHeader } from "./components/layout/AppHeader";
import { ResultsPanel } from "./components/results/ResultsPanel";
import type { MaskMode } from "./lib/masking";
import type { Detection } from "./types/detection";

type CoachMarkVariant = "intro" | "result";

export function App() {
  const [inputText, setInputText] = useState("");
  const [scanned, setScanned] = useState<{ text: string; detections: Detection[] } | null>(null);
  const [scanRun, setScanRun] = useState(0);
  const [coachMarkVariant, setCoachMarkVariant] = useState<CoachMarkVariant | null>("intro");
  const [maskMode, setMaskMode] = useState<MaskMode>("mask");
  // "탐지 결과 조정" 패널이 항목별 가림/보임 조정을 반영한 최종본을 계산해 여기로 보고한다 —
  // 그래야 왼쪽 결과 박스·복사 버튼이 항상 오른쪽 패널의 조정 상태와 같은 텍스트를 본다.
  const [maskedResultText, setMaskedResultText] = useState("");
  // 결과 코치마크는 첫 스캔 직후 딱 한 번만 자동으로 뜬다 — 재스캔마다 다시 뜨면 방해가 된다(#299).
  const hasAutoShownResultCoachMark = useRef(false);

  const displayText = scanned ? maskedResultText : inputText;

  function handleResult(text: string, detections: Detection[]) {
    setScanned({ text, detections });
    setScanRun((run) => run + 1);
    if (!hasAutoShownResultCoachMark.current) {
      hasAutoShownResultCoachMark.current = true;
      setCoachMarkVariant("result");
    }
  }

  function handleClear() {
    setInputText("");
    setScanned(null);
    setMaskedResultText("");
  }

  function handleTextChange(text: string) {
    setInputText(text);
    if (scanned) {
      setScanned(null);
      setMaskedResultText("");
    }
  }

  function dismissCoachMark() {
    setCoachMarkVariant(null);
  }

  function openCoachMark() {
    setCoachMarkVariant(scanned ? "result" : "intro");
  }

  return (
    <div className="app-shell">
      <AppHeader onHelpClick={openCoachMark} />

      <div className="privacy-note" role="note" aria-label="개인정보 입력 주의 안내">
        <span className="privacy-note__icon" aria-hidden="true">▣</span>
        <span>
          이 데모는 시연·학습용입니다. <strong>실제 개인정보를 입력하지 마세요.</strong> 입력 내용은
          저장되지 않으며, 로컬(브라우저 ↔ 로컬 API)에서만 처리됩니다. 실사용은 로컬 설치를 권장합니다.
        </span>
      </div>

      <main className="app-grid">
        <section className="panel panel--main">
          <InputPanel
            text={displayText}
            hasResult={Boolean(scanned)}
            resultVersion={scanRun}
            maskMode={maskMode}
            onMaskModeChange={setMaskMode}
            onTextChange={handleTextChange}
            onClear={handleClear}
            onResult={handleResult}
          />
        </section>

        <ResultsPanel
          scanned={scanned}
          scanRun={scanRun}
          maskMode={maskMode}
          onMaskedTextChange={setMaskedResultText}
        />
      </main>

      <footer className="accuracy-note" role="note" aria-label="이름 탐지 정확도 안내">
        <span className="accuracy-note__icon" aria-hidden="true">ⓘ</span>
        <span>
          이 웹 데모는 <strong>규칙 기반 탐지만</strong> 사용합니다. 문맥 단서가 없는 이름 일부는 놓칠 수
          있어요 —{" "}
          <a href="https://github.com/ChoHyeonChan/maskingtape" target="_blank" rel="noopener noreferrer">
            로컬 설치
          </a>{" "}
          후 <code>--llm</code> 옵션을 쓰면 로컬 LLM으로 이름까지 더 정확하게 탐지합니다.
        </span>
      </footer>

      {coachMarkVariant && <CoachMark variant={coachMarkVariant} onDismiss={dismissCoachMark} />}
    </div>
  );
}
