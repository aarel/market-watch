# Fly.io Deployment (FastAPI Backend)

## Prerequisites
- Fly.io account
- `flyctl` installed

Install `flyctl`:
```bash
# macOS / Linux
curl -L https://fly.io/install.sh | sh

# Windows (PowerShell)
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

Authenticate:
```bash
fly auth login
```

## First Deploy
From repo root:
```bash
fly launch --copy-config --no-deploy
fly deploy
fly open
```

Notes:
- `fly.toml` is pre-created in this repo.
- Default app name in `fly.toml` is `market-watch-demo`; change `app = ...` to a unique name if needed.

## Runtime Config
Set required secrets/environment before deploy (example):
```bash
fly secrets set ALPACA_API_KEY=... ALPACA_SECRET_KEY=...
fly secrets set TRADING_MODE=paper AUTO_TRADE=false MARKET_WATCH_DEMO_MODE=true FASTAPI_DISABLE_LIFESPAN=0
```

## Verification
Get app URL:
```bash
fly status
```

Health checks:
```bash
curl https://<your-app>.fly.dev/health
curl https://<your-app>.fly.dev/api/health
```

Expected:
- HTTP 200
- JSON containing either `{"status":"healthy"}` (`/health`) or service health payload (`/api/health`).

Optional API smoke checks:
```bash
curl https://<your-app>.fly.dev/api/config
curl https://<your-app>.fly.dev/api/observability/logs
```

## Redeploy
```bash
fly deploy
```
