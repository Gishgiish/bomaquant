# BomaQuant Backend

## Quick start

```bash
cd /home/drunk-rick/bomaquant
./venv/bin/python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- GET /health
- GET /health/ready
- GET /stocks/{symbol}
- GET /market/summary
- POST /jobs
- GET /jobs/{job_id}

## Configuration

Copy [.env.example](.env.example) to .env to override local settings such as auth and API credentials.

## Current status

The backend now has a minimal FastAPI application shell, readiness checks, config-driven auth, structured logging, provider-backed market data access, background analysis jobs, and automated API tests for the main routes. The current implementation also records explicit failure states for analysis jobs when the analysis bridge errors. The first milestone for the premium architecture is now in place with a repository abstraction for job storage and a lightweight worker abstraction that decouples job dispatch from persistence.

## Deployment and operations

### Local container stack

```bash
docker compose up --build
```

The compose file exposes the backend on port 8000 and mounts a persistent SQLite volume at /app/data for local job persistence.

### Production checklist

- Set real secrets for AUTH_ENABLED, API_USERNAME, API_PASSWORD, and NSE_RAPIDAPI_KEY.
- Use a production-grade reverse proxy or platform-managed ingress in front of the FastAPI service.
- Keep the data directory on a persistent volume if you rely on SQLite-backed job storage.
- Review the environment overrides in [.env.example](.env.example) before deployment.

For a deeper runbook, see [docs/DEPLOYMENT_GUIDANCE.md](docs/DEPLOYMENT_GUIDANCE.md).
