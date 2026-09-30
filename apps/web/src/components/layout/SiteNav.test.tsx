// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SiteNav } from "./SiteNav";

describe("SiteNav help button tooltip", () => {
  it("carries a data-tooltip so its label shows immediately on hover, not the browser's delayed title tooltip", () => {
    render(<SiteNav onHelpClick={() => {}} />);
    const helpButton = screen.getByRole("button", { name: "사용 안내 다시 보기" });
    expect(helpButton).toHaveAttribute("data-tooltip", "도움말");
  });
});

describe("SiteNav logo (layout-shift regression)", () => {
  it("declares explicit width/height so the browser reserves space before the image loads", () => {
    // 로고에 width/height(또는 CSS aspect-ratio)가 없으면, 이미지가 로드되기 전엔 높이가
    // 0이었다가 로드 후 실제 크기만큼 레이아웃이 밀려난다. width/height 속성을 주면 브라우저가
    // 이미지 도착 전부터 최종 공간을 미리 잡아 둬 로드 후에도 레이아웃이 움직이지 않는다.
    render(<SiteNav onHelpClick={() => {}} />);
    const logo = screen.getByRole("img", { name: "MaskingTape" });
    expect(logo).toHaveAttribute("width");
    expect(logo).toHaveAttribute("height");

    const width = Number(logo.getAttribute("width"));
    const height = Number(logo.getAttribute("height"));
    // 실제 파일(1501x276)과 다른 비율이면 지정해도 무의미하다 — 원본 비율과 일치하는지 확인.
    expect(width / height).toBeCloseTo(1501 / 276, 2);
  });
});

describe("SiteNav 오픈소스 고지 링크 (#439)", () => {
  it("links to THIRD_PARTY_NOTICES.md and opens it in a new tab", () => {
    render(<SiteNav onHelpClick={() => {}} />);
    const link = screen.getByRole("link", { name: "오픈소스 라이선스" });

    expect(link).toHaveAttribute(
      "href",
      "https://github.com/ChoHyeonChan/maskingtape/blob/main/THIRD_PARTY_NOTICES.md",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});

describe("SiteNav section links", () => {
  it("links to every landing page section by id", () => {
    render(<SiteNav onHelpClick={() => {}} />);

    expect(screen.getByRole("link", { name: "소개" })).toHaveAttribute("href", "#intro");
    expect(screen.getByRole("link", { name: "탐지 범위" })).toHaveAttribute("href", "#coverage");
    expect(screen.getByRole("link", { name: "정확도" })).toHaveAttribute("href", "#accuracy");
    expect(screen.getByRole("link", { name: "체험하기" })).toHaveAttribute("href", "#demo");
    expect(screen.getByRole("link", { name: "웹에서 체험하기" })).toHaveAttribute("href", "#demo");
  });
});

describe("SiteNav accuracy bubble (도움말 옆에 잠깐 뜨는 정확도 안내)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the rule-based-detection caveat next to the help button on mount", () => {
    render(<SiteNav onHelpClick={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("로컬 설치를 권장합니다");
  });

  it("does not dismiss just because the page was clicked elsewhere", () => {
    render(<SiteNav onHelpClick={() => {}} />);
    expect(screen.getByRole("status")).toBeInTheDocument();

    fireEvent.click(document.body);

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("dismisses when its own X (close) button is clicked", () => {
    render(<SiteNav onHelpClick={() => {}} />);
    expect(screen.getByRole("status")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "정확도 안내 닫기" }));

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("auto-dismisses after 30 seconds even without a click", () => {
    render(<SiteNav onHelpClick={() => {}} />);
    expect(screen.getByRole("status")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(30_000);
    });

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows again when a scan result first appears, even if it already timed out on the first page", () => {
    const { rerender } = render(<SiteNav onHelpClick={() => {}} hasResult={false} />);

    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<SiteNav onHelpClick={() => {}} hasResult={true} />);

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("does not re-show on every re-render while a result is already displayed", () => {
    const { rerender } = render(<SiteNav onHelpClick={() => {}} hasResult={true} />);

    fireEvent.click(screen.getByRole("button", { name: "정확도 안내 닫기" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<SiteNav onHelpClick={() => {}} hasResult={true} />);

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("hides while the coachmark overlay is active, since both use the same red dismiss-hint styling and clash", () => {
    const { rerender } = render(<SiteNav onHelpClick={() => {}} coachMarkActive={true} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<SiteNav onHelpClick={() => {}} coachMarkActive={false} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
