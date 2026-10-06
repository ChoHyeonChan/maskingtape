// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { useRef, useState } from "react";
import { CoachMark } from "../components/help/CoachMark";
import { InputPanel } from "../components/input/InputPanel";
import { SiteNav } from "../components/layout/SiteNav";
import { ResultsPanel } from "../components/results/ResultsPanel";
import type { MaskMode } from "../lib/masking";
import type { Detection, HighlightRange } from "../types/detection";

type CoachMarkVariant = "intro" | "result";

// 실제 입력·결과 체험이 랜딩 페이지에서 이 별도 페이지로 옮겨왔다(#553 후속) — 탐지
// 범위(무엇을 잡나요)는 다시 랜딩으로 돌아갔다. 상호작용은 여기서만 일어나므로 스캔
// 상태·코치마크도 App.tsx가 아니라 여기서 들고 있는다.
export function DemoPage() {
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
    <>
      <SiteNav
        variant="demo"
        onHelpClick={openCoachMark}
        hasResult={Boolean(scanned)}
        coachMarkActive={coachMarkVariant !== null}
      />
      <div className="app-shell">
        <div className="experience" id="demo">
          <div className="privacy-note" role="note" aria-label="개인정보 입력 주의 안내">
            <span className="privacy-note__icon" aria-hidden="true">▣</span>
            <span>
              이 데모는 시연·학습용입니다. 실제 개인정보는 입력하지 마세요 — 입력한 글은 분석을 위해 서버로
              전송되며, 우리 코드는 요청 내용을 저장하거나 기록하지 않습니다.{" "}
              <strong>정확한 결과가 필요하면 로컬 설치를 권장합니다.</strong>
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
        </div>

        {coachMarkVariant && <CoachMark variant={coachMarkVariant} onDismiss={dismissCoachMark} />}
      </div>
    </>
  );
}
