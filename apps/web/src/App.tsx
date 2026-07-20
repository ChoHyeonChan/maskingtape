import { useState } from "react";
import { HighlightedText } from "./components/HighlightedText";
import { InputPanel } from "./components/InputPanel";
import type { Detection } from "./types/detection";

export function App() {
  const [scanned, setScanned] = useState<{ text: string; detections: Detection[] } | null>(null);

  return (
    <div className="app">
      <header className="app__header">
        <h1>maskingtape 웹 플레이그라운드</h1>
        <p>텍스트를 붙여넣으면 한국어 개인정보를 탐지해 종류별로 하이라이트합니다.</p>
      </header>

      <main className="app__main">
        <InputPanel onResult={(text, detections) => setScanned({ text, detections })} />

        <section aria-label="탐지 결과">
          <h2>탐지 결과</h2>
          <HighlightedText text={scanned?.text ?? ""} detections={scanned?.detections ?? []} />
        </section>
      </main>
    </div>
  );
}
