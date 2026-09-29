// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent as ReactMouseEvent, type TouchEvent as ReactTouchEvent } from "react";

interface Props {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (next: number) => void;
}

function pointFromEvent(event: MouseEvent | TouchEvent): { clientX: number } | null {
  if ("touches" in event) {
    const touch = event.touches[0] ?? event.changedTouches[0];
    return touch ? { clientX: touch.clientX } : null;
  }
  return { clientX: event.clientX };
}

/**
 * 확신도 임계값 조정 컨트롤 — 가로 막대를 직접 드래그(마우스/터치)하거나, 막대를 클릭해서
 * 그 지점의 값으로 바로 이동하거나, 화살표 클릭·키보드(방향키)로 step씩 오르내릴 수 있다.
 * 원형 다이얼판(#336)보다 먼저 있었던 막대 형태로, 디자인 담당 요청으로 되돌렸다.
 */
export function ConfidenceControl({ value, min, max, step, onChange }: Props) {
  const atMax = value >= max;
  const atMin = value <= min;
  const fillPct = ((value - min) / (max - min)) * 100;
  const trackRef = useRef<HTMLDivElement>(null);
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

  function valueFromPoint(clientX: number): number {
    const track = trackRef.current;
    if (!track) return value;
    const rect = track.getBoundingClientRect();
    const ratio = rect.width === 0 ? 0 : (clientX - rect.left) / rect.width;
    const raw = min + Math.min(1, Math.max(0, ratio)) * (max - min);
    const snapped = Math.round(raw / step) * step;
    return Math.min(max, Math.max(min, snapped));
  }

  function startDrag(clientX: number) {
    setDragging(true);
    onChange(valueFromPoint(clientX));
  }

  function handleMouseDown(event: ReactMouseEvent<HTMLDivElement>) {
    // 드래그 중 옆의 "N%" 텍스트가 브라우저 기본 텍스트 선택(파란 하이라이트)으로
    // 잡히는 걸 막는다 — 클릭 몇 번만 빠르게 해도 쉽게 발생한다.
    event.preventDefault();
    startDrag(event.clientX);
  }

  function handleTouchStart(event: ReactTouchEvent<HTMLDivElement>) {
    const touch = event.touches[0];
    if (!touch) return;
    startDrag(touch.clientX);
  }

  useEffect(() => {
    if (!dragging) return;

    function handleMove(event: MouseEvent | TouchEvent) {
      const point = pointFromEvent(event);
      if (point) onChange(valueFromPoint(point.clientX));
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
    <div className="confidence-bar">
      <div
        ref={trackRef}
        className={`confidence-bar__track${dragging ? " is-dragging" : ""}`}
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
      >
        <div className="confidence-bar__fill" style={{ width: `${fillPct}%` }} />
        <span className="confidence-bar__handle" style={{ left: `${fillPct}%` }} aria-hidden="true" />
      </div>
      <span className="confidence-bar__value">{value}%</span>
      <div className="confidence-bar__btns">
        <button
          type="button"
          className="confidence-bar__btn"
          onClick={increase}
          disabled={atMax}
          aria-label="확신도 임계값 올리기"
        >
          ▲
        </button>
        <button
          type="button"
          className="confidence-bar__btn"
          onClick={decrease}
          disabled={atMin}
          aria-label="확신도 임계값 내리기"
        >
          ▼
        </button>
      </div>
    </div>
  );
}
