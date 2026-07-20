/**
 * 개발용 임시 프록시 — apps/api(기태 담당)가 아직 없어서 core CLI를 직접 호출해 /api/scan을 흉내낸다.
 * apps/api의 POST /scan이 완성되면 이 파일과 vite.config.ts의 플러그인 등록을 지우고
 * fetch("/api/scan")를 실제 API 주소로 바꾸면 된다 — scanClient.ts 쪽 인터페이스는 그대로 유지.
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import type { Connect, Plugin } from "vite";

const REPO_ROOT = resolve(import.meta.dirname, "../../..");

function findPython(): string {
  const candidates = [
    resolve(REPO_ROOT, ".venv/Scripts/python.exe"), // Windows venv
    resolve(REPO_ROOT, ".venv/bin/python"), // macOS/Linux venv
  ];
  return candidates.find((p) => existsSync(p)) ?? "python3";
}

function readBody(req: Connect.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

export function scanProxyPlugin(): Plugin {
  return {
    name: "maskingtape-dev-scan-proxy",
    configureServer(server) {
      server.middlewares.use("/api/scan", async (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 405;
          res.end("POST만 지원합니다");
          return;
        }

        let text: string;
        try {
          const body = JSON.parse(await readBody(req));
          text = body.text ?? "";
        } catch {
          res.statusCode = 400;
          res.end("잘못된 요청 본문 (JSON { text } 형식이어야 함)");
          return;
        }

        const python = findPython();
        const child = spawn(python, ["-m", "maskingtape.cli", "--scan"], {
          cwd: REPO_ROOT,
          env: { ...process.env, PYTHONIOENCODING: "utf-8" },
        });

        let stdout = "";
        let stderr = "";
        child.stdout.on("data", (chunk) => (stdout += chunk));
        child.stderr.on("data", (chunk) => (stderr += chunk));
        child.stdin.end(text);

        child.on("close", (code) => {
          if (code !== 0) {
            res.statusCode = 500;
            res.setHeader("Content-Type", "application/json; charset=utf-8");
            res.end(
              JSON.stringify({
                error: `core CLI 실행 실패 (${python}). packages/core가 venv에 설치돼 있는지 확인하세요: pip install -e packages/core`,
                detail: stderr.trim(),
              }),
            );
            return;
          }
          res.statusCode = 200;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ detections: JSON.parse(stdout) }));
        });
      });
    },
  };
}
