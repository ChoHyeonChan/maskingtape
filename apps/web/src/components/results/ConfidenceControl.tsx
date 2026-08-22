import type { CSSProperties, KeyboardEvent } from "react";

interface Props {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (next: number) => void;
}

/**
 * 마스킹 강도 조정 컨트롤 — 안1: 원형 게이지 + 위/아래 화살표.
 * 드래그가 필요한 가로 슬라이더 대신, 링이 강도만큼 채워지고 화살표로 step씩 오르내린다.
 */
export function ConfidenceControl({ value, min, max, step, onChange }: Props) {
  const atMax = value >= max;
  const atMin = value <= min;
  const fillPct = ((value - min) / (max - min)) * 100;

  function increase() {
    onChange(Math.min(max, value + step));
  }

  function decrease() {
    onChange(Math.max(min, value - step));
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === "ArrowUp" || event.key === "ArrowRight") {
      event.preventDefault();
      increase();
    } else if (event.key === "ArrowDown" || event.key === "ArrowLeft") {
      event.preventDefault();
      decrease();
    }
  }

  return (
    <div className="confidence-dial">
      <button
        type="button"
        className="confidence-dial__btn"
        onClick={increase}
        disabled={atMax}
        aria-label="마스킹 강도 올리기"
      >
        ▲
      </button>
      <div
        className="confidence-dial__ring"
        role="spinbutton"
        aria-label="마스킹 강도"
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuetext={`${value}%`}
        tabIndex={0}
        onKeyDown={handleKeyDown}
        style={{ "--dial-fill": `${fillPct}%` } as CSSProperties}
      >
        <span className="confidence-dial__value">{value}%</span>
      </div>
      <button
        type="button"
        className="confidence-dial__btn"
        onClick={decrease}
        disabled={atMin}
        aria-label="마스킹 강도 내리기"
      >
        ▼
      </button>
    </div>
  );
}
