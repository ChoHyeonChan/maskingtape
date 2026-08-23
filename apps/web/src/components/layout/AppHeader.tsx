interface Props {
  onHelpClick: () => void;
}

export function AppHeader({ onHelpClick }: Props) {
  return (
    <header className="app-header">
      <div className="app-header__content">
        <img
          className="brand-logo"
          src="/maskingtape-logo-blue.png"
          alt="MaskingTape"
          width={1501}
          height={276}
        />
        <p>한국어 문서 속 개인정보를 탐지하고, 안전하게 마스킹해 공유할 수 있게 돕습니다.</p>
      </div>

      <button
        type="button"
        className="help-button"
        aria-label="사용 안내 다시 보기"
        data-tooltip="도움말"
        onClick={onHelpClick}
      >
        i
      </button>
    </header>
  );
}
