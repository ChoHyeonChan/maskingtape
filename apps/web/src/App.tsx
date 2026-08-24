import { useRef, useState } from "react";
import { CoachMark } from "./components/help/CoachMark";
import { InputPanel } from "./components/input/InputPanel";
import { AppHeader } from "./components/layout/AppHeader";
import { ResultsPanel } from "./components/results/ResultsPanel";
import type { MaskMode } from "./lib/masking";
import type { Detection, HighlightRange } from "./types/detection";

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
  // 오른쪽 목록에서 항목에 마우스를 올렸을 때 왼쪽 "마스킹 결과" 텍스트의 해당 부분을
  // 강조하기 위한 범위 — 두 패널이 서로 멀리 떨어져 있어도 항목별 조정이 어디에
  // 해당하는지 바로 이어 보이게 한다.
  const [highlight, setHighlight] = useState<HighlightRange | null>(null);
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
    setHighlight(null);
  }

  function handleTextChange(text: string) {
    setInputText(text);
    if (scanned) {
      setScanned(null);
      setMaskedResultText("");
      setHighlight(null);
    }
  }

  // "마스킹 결과" 박스를 클릭해서 직접 고쳐 다시 탐지하고 싶을 때 — "초기화 하기"와
  // 달리 입력했던 원문(inputText)은 그대로 두고 결과만 지워서 편집 가능한 입력 상태로
  // 돌아간다. displayText는 scanned가 null이 되는 순간 원문을 다시 보여준다.
  function handleRequestEdit() {
    setScanned(null);
    setMaskedResultText("");
    setHighlight(null);
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
          이 데모는 시연·학습용입니다. 실제 개인정보를 입력하지 마세요. 입력 내용은
          저장되지 않으며, 로컬(브라우저 ↔ 로컬 API)에서만 처리됩니다. <strong>실사용은 로컬 설치를 권장합니다.</strong>
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
            onRequestEdit={handleRequestEdit}
            highlight={highlight}
          />
        </section>

        <ResultsPanel
          scanned={scanned}
          scanRun={scanRun}
          maskMode={maskMode}
          onMaskedTextChange={setMaskedResultText}
          onHighlightChange={setHighlight}
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
