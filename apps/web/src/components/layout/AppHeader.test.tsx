import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppHeader } from "./AppHeader";

describe("AppHeader help button tooltip", () => {
  it("carries a data-tooltip so its label shows immediately on hover, not the browser's delayed title tooltip", () => {
    render(<AppHeader onHelpClick={() => {}} />);
    const helpButton = screen.getByRole("button", { name: "사용 안내 다시 보기" });
    expect(helpButton).toHaveAttribute("data-tooltip", "도움말");
  });
});

describe("AppHeader logo (layout-shift regression)", () => {
  it("declares explicit width/height so the browser reserves space before the image loads", () => {
    // 로고에 width/height(또는 CSS aspect-ratio)가 없으면, 이미지가 로드되기 전엔 높이가
    // 0이었다가 로드 후 실제 크기(약 62px)만큼 아래 레이아웃이 밀려난다. 첫 진입 때 이
    // 밀림이 코치마크가 측정해둔 좌표보다 늦게 일어나면(느린 네트워크·캐시 없음),
    // 코치마크 하이라이트가 실제 버튼 위치와 어긋난 채로 남는다 — 새로고침하면 이미지가
    // 캐시돼 있어 재현되지 않아서 원인 파악이 어려웠다. width/height 속성을 주면 브라우저가
    // 이미지 도착 전부터 최종 공간을 미리 잡아 둬 로드 후에도 레이아웃이 움직이지 않는다.
    render(<AppHeader onHelpClick={() => {}} />);
    const logo = screen.getByRole("img", { name: "MaskingTape" });
    expect(logo).toHaveAttribute("width");
    expect(logo).toHaveAttribute("height");

    const width = Number(logo.getAttribute("width"));
    const height = Number(logo.getAttribute("height"));
    // 실제 파일(1501x276)과 다른 비율이면 지정해도 무의미하다 — 원본 비율과 일치하는지 확인.
    expect(width / height).toBeCloseTo(1501 / 276, 2);
  });
});

describe("AppHeader accuracy bubble (도움말 옆에 잠깐 뜨는 정확도 안내)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the rule-based-detection caveat next to the help button on mount", () => {
    render(<AppHeader onHelpClick={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("규칙 기반 탐지만");
  });

  it("dismisses on any click anywhere on the page", () => {
    render(<AppHeader onHelpClick={() => {}} />);
    expect(screen.getByRole("status")).toBeInTheDocument();

    fireEvent.click(document.body);

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("auto-dismisses after 30 seconds even without a click", () => {
    render(<AppHeader onHelpClick={() => {}} />);
    expect(screen.getByRole("status")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(30_000);
    });

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
