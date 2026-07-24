interface Props {
  onHelpClick: () => void;
}

export function AppHeader({ onHelpClick }: Props) {
  return (
    <header className="app-header">
      <div>
        <span className="app-header__eyebrow">개인정보 비식별화 데모</span>
        <h1>마스킹테이프 웹 플레이그라운드</h1>
        <p>텍스트를 탐지하고, 필요한 개인정보만 클릭해서 테이프처럼 가릴 수 있습니다.</p>
      </div>

      <button type="button" className="help-button" aria-label="도움말 다시 보기" onClick={onHelpClick}>
        i
      </button>
    </header>
  );
}
