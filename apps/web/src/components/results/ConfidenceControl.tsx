import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type MouseEvent as ReactMouseEvent, type TouchEvent as ReactTouchEvent } from "react";

interface Props {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (next: number) => void;
}

function pointFromEvent(event: MouseEvent | TouchEvent): { clientX: number; clientY: number } | null {
  if ("touches" in event) {
    const touch = event.touches[0] ?? event.changedTouches[0];
    return touch ? { clientX: touch.clientX, clientY: touch.clientY } : null;
  }
  return { clientX: event.clientX, clientY: event.clientY };
}

/**
 * 확신도 임계값 조정 컨트롤 — 원형 링을 직접 드래그(마우스/터치)해서 조정하거나,
 * 화살표 클릭·키보드(방향키)로 step씩 오르내릴 수 있다. 링 위 어디를 눌러도
 * 그 각도에 해당하는 값으로 바로 이동한다(12시 방향=0%, 시계 방향으로 증가).
 */
export function ConfidenceControl({ value, min, max, step, onChange }: Props) {
  const atMax = value >= max;
  const atMin = value <= min;
  const fillPct = ((value - min) / (max - min)) * 100;
  const ringRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);

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

  function valueFromPoint(clientX: number, clientY: number): number {
    const ring = ringRef.current;
    if (!ring) return value;
    const rect = ring.getBoundingClientRect();
    const dx = clientX - (rect.left + rect.width / 2);
    const dy = clientY - (rect.top + rect.height / 2);
    let angle = Math.atan2(dx, -dy);
    if (angle < 0) angle += Math.PI * 2;
    const raw = min + (angle / (Math.PI * 2)) * (max - min);
    const snapped = Math.round(raw / step) * step;
    return Math.min(max, Math.max(min, snapped));
  }

  function startDrag(clientX: number, clientY: number) {
    setDragging(true);
    onChange(valueFromPoint(clientX, clientY));
  }

  function handleMouseDown(event: ReactMouseEvent<HTMLDivElement>) {
    // 드래그 중 안의 "N%" 텍스트가 브라우저 기본 텍스트 선택(파란 하이라이트)으로
    // 잡히는 걸 막는다 — 클릭 몇 번만 빠르게 해도 쉽게 발생한다.
    event.preventDefault();
    startDrag(event.clientX, event.clientY);
  }

  function handleTouchStart(event: ReactTouchEvent<HTMLDivElement>) {
    const touch = event.touches[0];
    if (!touch) return;
    startDrag(touch.clientX, touch.clientY);
  }

  useEffect(() => {
    if (!dragging) return;

    function handleMove(event: MouseEvent | TouchEvent) {
      const point = pointFromEvent(event);
      if (point) onChange(valueFromPoint(point.clientX, point.clientY));
    }
    function stopDrag() {
      setDragging(false);
    }

    window.addEventListener("mousemove", handleMove);
    window.addEventListener("touchmove", handleMove);
    window.addEventListener("mouseup", stopDrag);
    window.addEventListener("touchend", stopDrag);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("touchmove", handleMove);
      window.removeEventListener("mouseup", stopDrag);
      window.removeEventListener("touchend", stopDrag);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dragging, min, max, step]);

  return (
    <div className="confidence-dial">
      <button
        type="button"
        className="confidence-dial__btn"
        onClick={increase}
        disabled={atMax}
        aria-label="확신도 임계값 올리기"
      >
        ▲
      </button>
      <div
        ref={ringRef}
        className={`confidence-dial__ring${dragging ? " is-dragging" : ""}`}
        role="spinbutton"
        aria-label="확신도 임계값"
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuetext={`${value}%`}
        tabIndex={0}
        onKeyDown={handleKeyDown}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        style={{ "--dial-fill": `${fillPct}%` } as CSSProperties}
      >
        <div
          className="confidence-dial__handle-track"
          style={{ transform: `rotate(${(fillPct / 100) * 360}deg)` } as CSSProperties}
        >
          <span className="confidence-dial__handle" aria-hidden="true" />
        </div>
        <span className="confidence-dial__value">{value}%</span>
      </div>
      <button
        type="button"
        className="confidence-dial__btn"
        onClick={decrease}
        disabled={atMin}
        aria-label="확신도 임계값 내리기"
      >
        ▼
      </button>
    </div>
  );
}
