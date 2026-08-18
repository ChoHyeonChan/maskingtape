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

type TargetKey = "presets" | "scan" | "masked-result" | "analysis-result";

interface CoachTarget {
  key: TargetKey;
  label: string;
  side: "above" | "below";
  note: Rect;
  rect: Rect;
}

type RawCoachTarget = Omit<CoachTarget, "note">;

const TARGET_KEYS: Record<Variant, TargetKey[]> = {
  intro: ["presets", "scan"],
  result: ["masked-result", "analysis-result"],
};

const TARGET_COPY: Record<TargetKey, string> = {
  presets: "입력할 문장이 없다면 예제로 먼저 확인해 보세요.",
  scan: "텍스트를 입력한 뒤 탐지를 실행하면 결과가 오른쪽에 표시됩니다.",
  "masked-result": "마스킹된 결과가 여기 표시돼요. 복사 버튼으로 바로 가져갈 수 있어요.",
  "analysis-result": "탐지된 개인정보 종류와 확신도를 여기서 확인하고, 카드를 눌러 필터링할 수 있어요.",
};

// 노트가 대상 위/아래 중 어느 쪽에 뜨는지 — scan 버튼은 패널 아래쪽에 있어 노트를 아래에 두면
// 화면 밖으로 밀려나므로 위쪽에 띄운다. 나머지는 모두 패널 상단부라 아래쪽이 자연스럽다.
const TARGET_SIDE: Record<TargetKey, "above" | "below"> = {
  presets: "below",
  scan: "above",
  "masked-result": "below",
  "analysis-result": "below",
};

const TARGET_PADDING: Record<TargetKey, number> = {
  presets: 7,
  scan: 8,
  "masked-result": 7,
  "analysis-result": 7,
};

const MINI_COPY: Record<Variant, { title: string; body: string }> = {
  intro: { title: "처음이라면", body: "예제 선택, 개인정보 탐지, 결과에서 값 가리기 순서로 살펴보세요." },
  result: { title: "완료!", body: "카드를 눌러 필터링하고, 하이라이트된 값을 눌러 직접 가려볼 수 있어요." },
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

      <div className="coachmark__mini">
        <strong>{mini.title}</strong>
        <span>{mini.body}</span>
      </div>
    </div>
  );
}
