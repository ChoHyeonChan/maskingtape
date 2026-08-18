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
    render(<CoachMark onDismiss={onDismiss} />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("does not dismiss on unrelated key presses", () => {
    const onDismiss = vi.fn();
    render(<CoachMark onDismiss={onDismiss} />);

    fireEvent.keyDown(window, { key: "Enter" });

    expect(onDismiss).not.toHaveBeenCalled();
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

    const { container } = render(<CoachMark onDismiss={vi.fn()} />);

    expect(container.querySelectorAll(".coachmark__focus")).toHaveLength(1);
    expect(container.querySelector(".coachmark__note")?.textContent).toContain(
      "텍스트를 입력한 뒤 탐지를 실행하면",
    );
  });
});
