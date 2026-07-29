interface Props {
  onHelpClick: () => void;
}

export function AppHeader({ onHelpClick }: Props) {
  return (
    <header className="app-header">
      <div>
        <span className="app-header__eyebrow">개인정보 비식별화 데모</span>
        <h1>MaskingTape Playground</h1>
        <p>텍스트를 붙여넣으면 개인정보 탐지 결과와 마스킹 미리보기를 바로 확인할 수 있습니다.</p>
      </div>

      <button type="button" className="help-button" aria-label="사용 안내 다시 보기" onClick={onHelpClick}>
        i
      </button>
    </header>
  );
}
