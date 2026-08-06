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

      <aside className="privacy-note" aria-label="로컬 처리 안내">
        <span className="privacy-note__icon" aria-hidden="true">▣</span>
        <span>입력하신 데이터는 로컬에서만 처리되며, 외부로 전송되지 않습니다.</span>
      </aside>

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
