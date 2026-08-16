import { useState } from "react";
import { CoachMark } from "./components/help/CoachMark";
import { InputPanel } from "./components/input/InputPanel";
import { AppHeader } from "./components/layout/AppHeader";
import { ResultsPanel } from "./components/results/ResultsPanel";
import { applyMasking, type MaskMode } from "./lib/masking";
import type { Detection } from "./types/detection";

export function App() {
  const [inputText, setInputText] = useState("");
  const [scanned, setScanned] = useState<{ text: string; detections: Detection[] } | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [scanRun, setScanRun] = useState(0);
  const [showCoachMark, setShowCoachMark] = useState(true);
  const [maskMode, setMaskMode] = useState<MaskMode>("mask");

  // 결과 텍스트는 스캔 시점에 한 번만 만들어 저장하지 않고, 원문+탐지결과에서 매번 다시
  // 계산한다 — 그래야 마스킹 방식(별표/라벨) 토글을 바꿔도 별도 재스캔 없이 즉시 반영된다(#277).
  const displayText = scanned ? applyMasking(scanned.text, scanned.detections, maskMode) : inputText;

  function handleResult(text: string, detections: Detection[]) {
    setScanned({ text, detections });
    setActiveFilter(null);
    setScanRun((run) => run + 1);
  }

  function handleClear() {
    setInputText("");
    setScanned(null);
    setActiveFilter(null);
  }

  function handleTextChange(text: string) {
    setInputText(text);
    if (scanned) {
      setScanned(null);
      setActiveFilter(null);
    }
  }

  function dismissCoachMark() {
    setShowCoachMark(false);
  }

  return (
    <div className="app-shell">
      <AppHeader onHelpClick={() => setShowCoachMark(true)} />

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
          activeFilter={activeFilter}
          scanRun={scanRun}
          maskMode={maskMode}
          onFilterSelect={setActiveFilter}
        />
      </main>

      {showCoachMark && <CoachMark onDismiss={dismissCoachMark} />}
    </div>
  );
}
