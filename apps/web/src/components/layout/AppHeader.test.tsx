import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AppHeader } from "./AppHeader";

describe("AppHeader help button tooltip", () => {
  it("carries a data-tooltip so its label shows immediately on hover, not the browser's delayed title tooltip", () => {
    render(<AppHeader onHelpClick={() => {}} />);
    const helpButton = screen.getByRole("button", { name: "사용 안내 다시 보기" });
    expect(helpButton).toHaveAttribute("data-tooltip", "도움말");
  });
});
