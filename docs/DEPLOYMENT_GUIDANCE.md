# Deployment guidance

## Overview

This backend is designed to run locally with a lightweight Python environment and to be deployable behind a standard container runtime.

## Runtime expectations

- Python 3.12+
- A persistent volume for SQLite-backed analysis job data, typically mounted at /app/data
- Environment variables from .env or the deployment runtime

## Recommended deployment steps

1. Copy [.env.example](../.env.example) to a deployment-specific environment file.
2. Override the production values for auth and the NSE API key.
3. Build and run the container image with Docker Compose or a platform-native container runner.
4. Confirm the health and readiness endpoints before sending traffic.

## Health checks

- GET /health
- GET /health/ready

## Operational notes

- Keep API credentials in secret storage rather than committing them to source control.
- If you rely on SQLite for jobs, ensure the mounted storage persists across restarts.
- For higher availability, replace SQLite with a managed relational database later.
