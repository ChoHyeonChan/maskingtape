// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { useEffect, useLayoutEffect, useState } from "react";

type Variant = "intro" | "result";

interface Props {
  onDismiss: () => void;
  variant: Variant;
}

interface Rect {
  height: number;
  left: number;
  top: number;
  width: number;
}

type TargetKey = "scan" | "masked-result" | "analysis-result";

interface CoachTarget {
  key: TargetKey;
  label: string;
  side: "above" | "below";
  note: Rect;
  rect: Rect;
}

type RawCoachTarget = Omit<CoachTarget, "note">;

const TARGET_KEYS: Record<Variant, TargetKey[]> = {
  // #455 전엔 "presets"(예제 불러오기)도 함께 가리켰다 — 예제가 이제 페이지 위쪽 갤러리
  // 섹션으로 옮겨져 이미 눈에 띄므로, 인트로 투어는 실제 입력 동작인 scan 하나만 가리킨다.
  intro: ["scan"],
  result: ["masked-result", "analysis-result"],
};

const TARGET_COPY: Record<TargetKey, string> = {
  scan: "예제를 골랐거나 텍스트를 입력했다면, 여기를 눌러 개인정보를 탐지·마스킹하세요.",
  "masked-result": "마스킹된 결과가 여기 표시돼요. 복사 버튼으로 바로 가져갈 수 있어요.",
  "analysis-result": "탐지된 개인정보를 항목별로 확인하고, 토글로 가릴지 보일지 직접 정할 수 있어요.",
};

// 노트가 대상 위/아래 중 어느 쪽에 뜨는지 — scan 버튼은 패널 아래쪽에 있어 노트를 아래에 두면
// 화면 밖으로 밀려나므로 위쪽에 띄운다. 나머지는 모두 패널 상단부라 아래쪽이 자연스럽다.
const TARGET_SIDE: Record<TargetKey, "above" | "below"> = {
  scan: "above",
  "masked-result": "below",
  "analysis-result": "below",
};

const TARGET_PADDING: Record<TargetKey, number> = {
  scan: 8,
  "masked-result": 7,
  "analysis-result": 7,
};

const MINI_COPY: Record<Variant, { title: string; body: string }> = {
  intro: { title: "처음이라면", body: "예제 선택, 개인정보 탐지, 결과에서 값 가리기 순서로 살펴보세요." },
  result: { title: "완료!", body: "항목별 토글로 가릴지 보일지 직접 정할 수 있어요." },
};

function expandRect(rect: DOMRect, padding: number): Rect {
  return {
    height: rect.height + padding * 2,
    left: rect.left - padding,
    top: rect.top - padding,
    width: rect.width + padding * 2,
  };
}

function readTargets(variant: Variant): RawCoachTarget[] {
  return TARGET_KEYS[variant].flatMap((key) => {
    const element = document.querySelector<HTMLElement>(`[data-coach="${key}"]`);
    if (!element) return [];

    // 결과 화면에서는 예제 도구모음이 display:none으로 숨겨지지만 DOM에는 남아 있다.
    // 숨겨진 대상은 크기가 0인 사각형을 반환하므로, 그런 대상은 코치마크에서 제외한다.
    const bounds = element.getBoundingClientRect();
    if (bounds.width === 0 && bounds.height === 0) return [];

    return [
      {
        key,
        label: TARGET_COPY[key],
        side: TARGET_SIDE[key],
        rect: expandRect(bounds, TARGET_PADDING[key]),
      },
    ];
  });
}

function lineStyle(target: CoachTarget) {
  const startX = target.rect.left + target.rect.width + 7;
  const startY =
    target.side === "above" ? target.rect.top + target.rect.height * 0.72 : target.rect.top + target.rect.height * 0.55;
  const endX = target.note.left - 14;
  const endY = target.side === "above" ? target.note.top + target.note.height * 0.64 : target.note.top + target.note.height * 0.48;
  const bend = target.side === "above" ? 26 : -18;

  return `M ${startX} ${startY} C ${startX + 28} ${startY + bend}, ${endX - 28} ${endY}, ${endX} ${endY}`;
}

function noteStyle(target: RawCoachTarget) {
  const viewportWidth = window.innerWidth;
  const maxWidth = 430;
  const nextToTarget = target.rect.left + target.rect.width + 86;
  const left = Math.min(nextToTarget, viewportWidth - maxWidth - 24);

  return {
    height: 42,
    left: Math.max(24, left),
    top: target.side === "above" ? target.rect.top - 48 : target.rect.top + target.rect.height + 18,
    width: Math.min(maxWidth, viewportWidth - Math.max(24, left) - 24),
  };
}

function withNotes(targets: RawCoachTarget[]): CoachTarget[] {
  return targets.map((target) => ({
    ...target,
    note: noteStyle(target),
  }));
}

export function CoachMark({ onDismiss, variant }: Props) {
  const [targets, setTargets] = useState<CoachTarget[]>([]);

  useLayoutEffect(() => {
    function syncTargets() {
      setTargets(withNotes(readTargets(variant)));
    }

    syncTargets();
    window.addEventListener("resize", syncTargets);
    window.addEventListener("scroll", syncTargets, true);
    return () => {
      window.removeEventListener("resize", syncTargets);
      window.removeEventListener("scroll", syncTargets, true);
    };
  }, [variant]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onDismiss();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onDismiss]);

  // #455로 페이지 위에 소개·탐지범위·정확도·예제 섹션이 붙으면서 "체험" 영역(scan
  // 버튼 등)이 더 이상 화면 첫 화면(above the fold)에 있지 않다 — 코치마크가 뜰 때
  // 첫 대상을 화면 가운데로 스크롤해 보여주지 않으면 보이지도 않는 곳을 가리키게 된다.
  useEffect(() => {
    const firstKey = TARGET_KEYS[variant][0];
    const element = document.querySelector<HTMLElement>(`[data-coach="${firstKey}"]`);
    element?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [variant]);

  const mini = MINI_COPY[variant];

  return (
    <div className="coachmark" role="dialog" aria-modal="true" aria-label="사용 방법 안내" onClick={onDismiss}>
      <svg className="coachmark__scrim" aria-hidden="true">
        <defs>
          <mask id="coachmark-mask">
            <rect width="100%" height="100%" fill="white" />
            {targets.map((target) => (
              <rect
                key={`${target.key}-mask`}
                x={target.rect.left}
                y={target.rect.top}
                width={target.rect.width}
                height={target.rect.height}
                rx="18"
                fill="black"
              />
            ))}
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgba(15, 23, 42, 0.42)" mask="url(#coachmark-mask)" />
      </svg>

      {targets.map((target) => (
        <div
          key={`${target.key}-focus`}
          className="coachmark__focus"
          style={{
            height: target.rect.height,
            left: target.rect.left,
            top: target.rect.top,
            width: target.rect.width,
          }}
          aria-hidden="true"
        />
      ))}

      <svg className="coachmark__lines" aria-hidden="true">
        {targets.map((target) => (
          <path key={`${target.key}-line`} d={lineStyle(target)} />
        ))}
      </svg>

      {targets.map((target) => (
        <div
          key={`${target.key}-note`}
          className="coachmark__note"
          style={{
            left: target.note.left,
            top: target.note.top,
            width: target.note.width,
          }}
        >
          {target.label}
        </div>
      ))}

      <div className="coachmark__dismiss-hint" aria-hidden="true">
        아무 데나 누르면 닫힙니다
      </div>

      <div className="coachmark__mini">
        <strong>{mini.title}</strong>
        <span>{mini.body}</span>
      </div>
    </div>
  );
}
