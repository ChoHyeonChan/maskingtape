import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfidenceControl } from "./ConfidenceControl";

describe("ConfidenceControl (원형 링 드래그 + 화살표)", () => {
  it("shows the current value as plain text", () => {
    render(<ConfidenceControl value={80} min={0} max={100} step={5} onChange={() => {}} />);
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  it("calls onChange with the next step up when the up arrow is clicked", () => {
    const onChange = vi.fn();
    render(<ConfidenceControl value={80} min={0} max={100} step={5} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "확신도 임계값 올리기" }));
    expect(onChange).toHaveBeenCalledWith(85);
  });

  it("calls onChange with the next step down when the down arrow is clicked", () => {
    const onChange = vi.fn();
    render(<ConfidenceControl value={80} min={0} max={100} step={5} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "확신도 임계값 내리기" }));
    expect(onChange).toHaveBeenCalledWith(75);
  });

  it("clamps at max and disables the up arrow there", () => {
    render(<ConfidenceControl value={100} min={0} max={100} step={5} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "확신도 임계값 올리기" })).toBeDisabled();
  });

  it("clamps at min and disables the down arrow there", () => {
    render(<ConfidenceControl value={0} min={0} max={100} step={5} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "확신도 임계값 내리기" })).toBeDisabled();
  });

  it("supports arrow-key adjustment on the value itself", () => {
    const onChange = vi.fn();
    render(<ConfidenceControl value={80} min={0} max={100} step={5} onChange={onChange} />);
    fireEvent.keyDown(screen.getByRole("spinbutton"), { key: "ArrowUp" });
    expect(onChange).toHaveBeenCalledWith(85);

    fireEvent.keyDown(screen.getByRole("spinbutton"), { key: "ArrowDown" });
    expect(onChange).toHaveBeenCalledWith(75);
  });

  it("exposes the value to assistive tech via spinbutton ARIA attributes", () => {
    render(<ConfidenceControl value={80} min={0} max={100} step={5} onChange={() => {}} />);
    const spin = screen.getByRole("spinbutton");
    expect(spin).toHaveAttribute("aria-valuenow", "80");
    expect(spin).toHaveAttribute("aria-valuemin", "0");
    expect(spin).toHaveAttribute("aria-valuemax", "100");
    expect(spin).toHaveAttribute("aria-valuetext", "80%");
  });
});

function mockRingRect(ring: HTMLElement) {
  vi.spyOn(ring, "getBoundingClientRect").mockReturnValue({
    left: 0,
    top: 0,
    width: 100,
    height: 100,
    right: 100,
    bottom: 100,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  } as DOMRect);
}

describe("ConfidenceControl drag-to-adjust ring", () => {
  it("jumps to the value at the clicked angle (12시 방향 = 최솟값, 3시 방향 = 1/4바퀴)", () => {
    const onChange = vi.fn();
    render(<ConfidenceControl value={50} min={0} max={100} step={5} onChange={onChange} />);
    const ring = screen.getByRole("spinbutton");
    mockRingRect(ring);

    fireEvent.mouseDown(ring, { clientX: 50, clientY: 0 });
    expect(onChange).toHaveBeenLastCalledWith(0);

    fireEvent.mouseDown(ring, { clientX: 100, clientY: 50 });
    expect(onChange).toHaveBeenLastCalledWith(25);
  });

  it("keeps updating the value while dragging across the window, and stops reacting after mouseup", () => {
    const onChange = vi.fn();
    render(<ConfidenceControl value={0} min={0} max={100} step={5} onChange={onChange} />);
    const ring = screen.getByRole("spinbutton");
    mockRingRect(ring);

    fireEvent.mouseDown(ring, { clientX: 50, clientY: 0 });
    fireEvent.mouseMove(window, { clientX: 100, clientY: 50 });
    expect(onChange).toHaveBeenLastCalledWith(25);

    fireEvent.mouseUp(window);
    onChange.mockClear();
    fireEvent.mouseMove(window, { clientX: 0, clientY: 50 });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("also starts a drag from a touch point", () => {
    const onChange = vi.fn();
    render(<ConfidenceControl value={50} min={0} max={100} step={5} onChange={onChange} />);
    const ring = screen.getByRole("spinbutton");
    mockRingRect(ring);

    fireEvent.touchStart(ring, { touches: [{ clientX: 50, clientY: 100 }] });
    expect(onChange).toHaveBeenLastCalledWith(50);
  });
});
