import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App privacy banner (#154)", () => {
  it("always shows a privacy note warning against real personal data and describing local, unsaved processing", () => {
    render(<App />);

    const note = screen.getByRole("note", { name: "개인정보 입력 주의 안내" });
    expect(note).toHaveTextContent("실제 개인정보를 입력하지 마세요");
    expect(note).toHaveTextContent("저장되지 않으며");
    expect(note).toHaveTextContent("로컬");
  });
});
