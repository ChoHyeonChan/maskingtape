import { fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CoachMark } from "./CoachMark";

function stubRect(element: HTMLElement, rect: Partial<DOMRect>) {
  element.getBoundingClientRect = () =>
    ({ top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0, toJSON() {}, ...rect }) as DOMRect;
}

describe("CoachMark keyboard accessibility (#190)", () => {
  it("dismisses when Escape is pressed, without needing a mouse click", () => {
    const onDismiss = vi.fn();
    render(<CoachMark onDismiss={onDismiss} variant="intro" />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("does not dismiss on unrelated key presses", () => {
    const onDismiss = vi.fn();
    render(<CoachMark onDismiss={onDismiss} variant="intro" />);

    fireEvent.keyDown(window, { key: "Enter" });

    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("shows a hint that clicking anywhere dismisses it", () => {
    const { container } = render(<CoachMark onDismiss={vi.fn()} variant="intro" />);

    expect(container.querySelector(".coachmark__dismiss-hint")?.textContent).toBe("아무 데나 누르면 닫힙니다");
  });
});

describe("CoachMark target visibility", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("skips a coach target that is present in the DOM but hidden (e.g. behind display:none while a result is shown)", () => {
    const presets = document.createElement("button");
    presets.setAttribute("data-coach", "presets");
    document.body.appendChild(presets);
    stubRect(presets, { width: 0, height: 0 });

    const scan = document.createElement("button");
    scan.setAttribute("data-coach", "scan");
    document.body.appendChild(scan);
    stubRect(scan, { width: 120, height: 40, top: 200, left: 50, right: 170, bottom: 240 });

    const { container } = render(<CoachMark onDismiss={vi.fn()} variant="intro" />);

    expect(container.querySelectorAll(".coachmark__focus")).toHaveLength(1);
    expect(container.querySelector(".coachmark__note")?.textContent).toContain(
      "텍스트를 입력한 뒤 탐지를 실행하면",
    );
  });
});

describe("CoachMark result variant (#299)", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("targets the masked-result and analysis-result headers, not the intro targets, even if those are also present", () => {
    const scan = document.createElement("button");
    scan.setAttribute("data-coach", "scan");
    document.body.appendChild(scan);
    stubRect(scan, { width: 120, height: 40, top: 10, left: 10, right: 130, bottom: 50 });

    const maskedResult = document.createElement("h2");
    maskedResult.setAttribute("data-coach", "masked-result");
    document.body.appendChild(maskedResult);
    stubRect(maskedResult, { width: 140, height: 30, top: 80, left: 40, right: 180, bottom: 110 });

    const analysisResult = document.createElement("h2");
    analysisResult.setAttribute("data-coach", "analysis-result");
    document.body.appendChild(analysisResult);
    stubRect(analysisResult, { width: 140, height: 30, top: 80, left: 360, right: 500, bottom: 110 });

    const { container } = render(<CoachMark onDismiss={vi.fn()} variant="result" />);

    expect(container.querySelectorAll(".coachmark__focus")).toHaveLength(2);
    const noteText = Array.from(container.querySelectorAll(".coachmark__note")).map((note) => note.textContent);
    expect(noteText).toContainEqual(expect.stringContaining("마스킹된 결과가 여기 표시돼요"));
    expect(noteText).toContainEqual(expect.stringContaining("탐지된 개인정보 종류와 확신도"));
    expect(container.querySelector(".coachmark__mini strong")?.textContent).toBe("완료!");
  });

  it("shows the intro mini caption for the intro variant", () => {
    const { container } = render(<CoachMark onDismiss={vi.fn()} variant="intro" />);
    expect(container.querySelector(".coachmark__mini strong")?.textContent).toBe("처음이라면");
  });
});
