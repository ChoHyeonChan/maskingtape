# Vercel web demo deployment

This document is the deployment runbook for the public web demo. It is intentionally written as a checklist: do not mark the hosting issue done until the live URL has been tested.

## Hosting choice

Use one Vercel project from the repository root.

- `apps/web` is built as the static Vite frontend.
- `api/index.py` exports a FastAPI `app` mounted at `/api`.
- `pyproject.toml` + `uv.lock` install `packages/core` (`maskingtape`) and `apps/api` (`maskingtape-api`) into the Python function bundle. The local packages are declared with their correct names in `[tool.uv.sources]`. (A bare `-e ./apps/api` in `requirements.txt` made uv infer the wrong package name `api` and fail `uv lock` during the Vercel build — see #228.)
- The deployed browser calls same-origin `/api/scan`, so no cross-origin API URL is needed for the normal demo.

This follows the current Vercel Python/FastAPI model: a Python file under `api/` exports an ASGI `app`, dependencies are read from root Python dependency files, and the Vite build output is served as static assets.

## Required Vercel settings

Set these in Project Settings > Environment Variables before deploying production:

```text
MASKINGTAPE_API_ENV=production
MASKINGTAPE_API_CORS_ORIGINS=
MASKINGTAPE_API_RATE_LIMIT_REQUESTS=60
MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS=60
```

`MASKINGTAPE_API_CORS_ORIGINS` is intentionally empty for the single-origin Vercel deployment. Same-origin browser calls do not need CORS, and this avoids accidentally allowing `*`. If the web and API are ever split across domains, set this to the exact HTTPS web origin, for example `https://maskingtape.example`.

## Deploy

```powershell
npm.cmd exec --yes vercel@58.9.0 -- link
npm.cmd exec --yes vercel@58.9.0 -- env ls production
npm.cmd exec --yes vercel@58.9.0 -- deploy
npm.cmd exec --yes vercel@58.9.0 -- deploy --prod
```

Do not use a plain HTTP URL for the public demo. Vercel preview and production URLs are HTTPS by default.

## Verify the live URL

After deployment, run:

```powershell
python scripts/verify_web_demo_deployment.py https://<deployment-url> --check-rate-limit --rate-limit-attempts 65
```

The verifier checks:

- HTTPS URL
- static web root is reachable
- `/api/health` returns `{"status": "ok"}`
- `/api/scan` detects a synthetic passport number
- `/api/scan` detection metadata does not echo the raw PII value
- `/api/anonymize` masks the synthetic PII value
- hostile CORS origin is not allowed
- optional rate-limit check reaches 429

Also open the URL in a browser and confirm the visible privacy note warns users not to enter real personal information and says input is not stored.

## References

- Vercel FastAPI guide: <https://vercel.com/docs/frameworks/backend/fastapi>
- Vercel Python runtime: <https://vercel.com/docs/functions/runtimes/python>
- Vercel project configuration: <https://vercel.com/docs/project-configuration>
