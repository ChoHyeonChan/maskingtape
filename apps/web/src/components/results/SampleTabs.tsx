// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { PRESETS } from "../../lib/presets";
import { KIND_LABELS } from "../../types/detection";

interface Props {
  onPick: (text: string) => void;
}

/**
 * 스캔 전 비어 있던 "탐지 결과 조정" 자리를 샘플 문서 서랍으로 쓴다 — 서류철 인덱스처럼
 * 위쪽 탭(꼬리표)에 문서 유형을 달고, 탭을 고르면 그 샘플의 원문과 들어 있는 개인정보
 * 종류를 미리 보여준다. "입력창에 넣기"를 눌러야 실제 입력이 바뀌어, 둘러보기만 해도
 * 쓰던 글이 날아가지 않는다.
 */
export function SampleTabs({ onPick }: Props) {
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const active = PRESETS[activeIndex];

  // 탭이 패널 폭보다 많아 가로로 스크롤된다. 스크롤바는 탭과 본문이 이어지는 선을 끊어서
  // 숨겼으니, 마우스 휠(세로)도 탭 줄 위에서는 가로 스크롤로 바꿔 끝쪽 탭에 닿게 한다.
  // React의 onWheel은 passive라 preventDefault가 안 먹혀 직접 리스너를 단다.
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    function handleWheel(event: WheelEvent) {
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
      if (list!.scrollWidth <= list!.clientWidth) return;
      event.preventDefault();
      list!.scrollLeft += event.deltaY;
    }
    list.addEventListener("wheel", handleWheel, { passive: false });
    return () => list.removeEventListener("wheel", handleWheel);
  }, []);

  // WAI-ARIA 탭 패턴 — 좌우 화살표·Home·End로 탭을 옮기고 포커스도 함께 옮긴다.
  // focus()가 스크롤 밖에 있던 탭도 보이는 곳으로 끌어온다.
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const last = PRESETS.length - 1;
    const next =
      event.key === "ArrowRight"
        ? activeIndex === last ? 0 : activeIndex + 1
        : event.key === "ArrowLeft"
          ? activeIndex === 0 ? last : activeIndex - 1
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : null;
    if (next === null) return;
    event.preventDefault();
    setActiveIndex(next);
    tabRefs.current[next]?.focus();
  }

  return (
    <div className="sample-tabs">
      <p className="sample-tabs__lead">
        샘플 문서를 골라 입력창에 넣어보세요. 탐지를 실행하면 이 자리에 결과가 표시됩니다.
      </p>
      <div
        ref={listRef}
        className="sample-tabs__list"
        role="tablist"
        aria-label="샘플 문서"
        onKeyDown={handleKeyDown}
      >
        {PRESETS.map((preset, index) => (
          <button
            key={preset.label}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            type="button"
            role="tab"
            id={`sample-tab-${index}`}
            aria-selected={index === activeIndex}
            aria-controls="sample-tabs-panel"
            tabIndex={index === activeIndex ? 0 : -1}
            className="sample-tabs__tab"
            onClick={() => setActiveIndex(index)}
          >
            {preset.label}
          </button>
        ))}
      </div>
      <div
        className="sample-tabs__panel"
        role="tabpanel"
        id="sample-tabs-panel"
        aria-labelledby={`sample-tab-${activeIndex}`}
      >
        <div className="sample-tabs__kinds">
          {active.kinds.map((kind) => (
            <span key={kind} className="example-card__kind-tag">
              {KIND_LABELS[kind] ?? kind}
            </span>
          ))}
        </div>
        <p className="sample-tabs__preview">{active.text}</p>
        <button type="button" className="sample-tabs__use" onClick={() => onPick(active.text)}>
          입력창에 넣기
        </button>
      </div>
    </div>
  );
}
