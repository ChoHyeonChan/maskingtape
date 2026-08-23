import type { KeyboardEvent } from "react";

interface Props {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (next: number) => void;
}

/**
 * 확신도 임계값 조정 컨트롤 — 안2: 원형 게이지 그래픽 없이 숫자 + 위/아래 화살표.
 * 안1과 정보량·조작 방식은 동일하고(같은 step만큼 오르내림), 링 그래픽만 뺐다.
 */
export function ConfidenceControl({ value, min, max, step, onChange }: Props) {
  const atMax = value >= max;
  const atMin = value <= min;

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
    <div className="confidence-stepper">
      <button
        type="button"
        className="confidence-stepper__btn"
        onClick={increase}
        disabled={atMax}
        aria-label="확신도 임계값 올리기"
      >
        ▲
      </button>
      <span
        className="confidence-stepper__value"
        role="spinbutton"
        aria-label="확신도 임계값"
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuetext={`${value}%`}
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {value}%
      </span>
      <button
        type="button"
        className="confidence-stepper__btn"
        onClick={decrease}
        disabled={atMin}
        aria-label="확신도 임계값 내리기"
      >
        ▼
      </button>
    </div>
  );
}
