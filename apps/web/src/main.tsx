// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { StrictMode, type JSX } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { AccuracyPage } from "./pages/AccuracyPage";
import { DemoPage } from "./pages/DemoPage";
import "./index.css";

// 페이지가 몇 개뿐이라(랜딩, /accuracy, /demo) 라우터 없이 경로를 보고 고른다 — 셋 다
// <a href> 전체 이동(클라이언트 사이드 전환이 아님)으로만 오가므로 이 한 번의 분기로
// 충분하다. 페이지가 더 늘어나면 그때 react-router 도입을 고려한다.
const PAGES: Record<string, () => JSX.Element> = {
  "/accuracy": AccuracyPage,
  "/demo": DemoPage,
};
const RootPage = PAGES[window.location.pathname] ?? App;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootPage />
  </StrictMode>,
);
