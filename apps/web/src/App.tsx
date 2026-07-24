import { useState } from "react";
import { CoachMark } from "./components/help/CoachMark";
import { InputPanel } from "./components/input/InputPanel";
import { AppHeader } from "./components/layout/AppHeader";
import { ResultsPanel } from "./components/results/ResultsPanel";
import type { Detection } from "./types/detection";

export function App() {
  const [scanned, setScanned] = useState<{ text: string; detections: Detection[] } | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [scanRun, setScanRun] = useState(0);
  const [showCoachMark, setShowCoachMark] = useState(true);

  function handleResult(text: string, detections: Detection[]) {
    setScanned({ text, detections });
    setActiveFilter(null);
    setScanRun((run) => run + 1);
  }

  function dismissCoachMark() {
    setShowCoachMark(false);
  }

  return (
    <div className="app-shell">
      <AppHeader onHelpClick={() => setShowCoachMark(true)} />

      <main className="app-grid">
        <section className="panel panel--main">
          <InputPanel onResult={handleResult} />
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
