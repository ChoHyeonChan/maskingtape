// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccuracySection } from "./AccuracySection";

describe("AccuracySection (#455)", () => {
  it("shows the same overall F1 as README's 정확도 (공개 벤치마크) 표", () => {
    render(<AccuracySection />);
    expect(screen.getByRole("table")).toHaveTextContent("0.966");
  });

  it("links back to README as the source of the numbers", () => {
    render(<AccuracySection />);
    const link = screen.getByRole("link", { name: "README" });
    expect(link).toHaveAttribute("href", "https://github.com/ChoHyeonChan/maskingtape/blob/main/README.md");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("discloses the rule-only name recall caveat, not just the headline number", () => {
    render(<AccuracySection />);
    expect(screen.getAllByText(/0\.869/).length).toBeGreaterThan(0);
  });
});
