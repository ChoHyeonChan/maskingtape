// SPDX-FileCopyrightText: 2026 The maskingtape Authors
// SPDX-License-Identifier: Apache-2.0

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { AccuracyPage } from "./pages/AccuracyPage";
import "./index.css";

// 지금은 페이지가 둘뿐이라(랜딩, /accuracy) 라우터 없이 경로를 보고 고른다 — 둘 다
// <a href> 전체 이동(클라이언트 사이드 전환이 아님)으로만 오가므로 이 한 번의 분기로
// 충분하다. 페이지가 더 늘어나면 그때 react-router 도입을 고려한다.
const RootPage = window.location.pathname === "/accuracy" ? AccuracyPage : App;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootPage />
  </StrictMode>,
);
