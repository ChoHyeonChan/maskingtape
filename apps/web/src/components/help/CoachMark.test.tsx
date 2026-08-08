import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CoachMark } from "./CoachMark";

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
