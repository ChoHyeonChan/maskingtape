import { useState } from "react";
import { CoachMark } from "./components/help/CoachMark";
import { InputPanel } from "./components/input/InputPanel";
import { AppHeader } from "./components/layout/AppHeader";
import { ResultsPanel } from "./components/results/ResultsPanel";
import type { Detection } from "./types/detection";

export function App() {
  const [inputText, setInputText] = useState("");
  const [scanned, setScanned] = useState<{ text: string; detections: Detection[] } | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [scanRun, setScanRun] = useState(0);
  const [showCoachMark, setShowCoachMark] = useState(true);

  function handleResult(text: string, detections: Detection[]) {
    setInputText(maskText(text, detections));
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
            text={inputText}
            hasResult={Boolean(scanned)}
            resultVersion={scanRun}
            onTextChange={handleTextChange}
            onClear={handleClear}
            onResult={handleResult}
          />
        </section>

        <ResultsPanel
          scanned={scanned}
          activeFilter={activeFilter}
          scanRun={scanRun}
          onFilterSelect={setActiveFilter}
        />
      </main>

      {showCoachMark && <CoachMark onDismiss={dismissCoachMark} />}
    </div>
  );
}

function maskText(text: string, detections: Detection[]) {
  if (detections.length === 0) return text;

  let cursor = 0;
  let masked = "";

  for (const detection of [...detections].sort((a, b) => a.start - b.start || b.end - a.end)) {
    if (detection.start < cursor) continue;
    masked += text.slice(cursor, detection.start);
    masked += "*".repeat(detection.end - detection.start);
    cursor = detection.end;
  }

  return masked + text.slice(cursor);
}
