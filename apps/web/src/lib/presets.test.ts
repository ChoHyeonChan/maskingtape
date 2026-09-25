// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from "vitest";
import { KIND_LABELS } from "../types/detection";
import { PRESETS } from "./presets";

describe("PRESETS (#455)", () => {
  it("has more than the original 4 examples so the gallery shows real variety", () => {
    expect(PRESETS.length).toBeGreaterThanOrEqual(8);
  });

  it("gives every preset a non-empty label, body, and kind list", () => {
    for (const preset of PRESETS) {
      expect(preset.label.length).toBeGreaterThan(0);
      expect(preset.text.length).toBeGreaterThan(0);
      expect(preset.kinds.length).toBeGreaterThan(0);
    }
  });

  it("only declares kinds the UI knows how to label", () => {
    for (const preset of PRESETS) {
      for (const kind of preset.kinds) {
        expect(KIND_LABELS[kind], `${preset.label}의 kind "${kind}"에 라벨이 없음`).toBeDefined();
      }
    }
  });

  it("has unique labels so each preset can be identified in the UI", () => {
    const labels = PRESETS.map((preset) => preset.label);
    expect(new Set(labels).size).toBe(labels.length);
  });
});
