# Premium SaaS roadmap checklist

## Immediate priorities
- [x] Stabilize the backend API surface and job workflow
- [x] Introduce repository and worker abstractions for background work
- [x] Add domain models for portfolios and subscriptions
- [x] Add a provider registry for future multi-provider support
- [x] Add persistence for portfolios and subscriptions
- [x] Add a service layer for domain operations

## Next implementation waves
### Wave 1 — Product readiness
- [x] Add authentication-aware user profile storage
- [x] Add subscription plan enforcement in the API layer
- [x] Add feature-gated premium access rules for portfolio workflows
- [x] Add portfolio CRUD and watchlist management endpoints
- [x] Add audit logging for creation and update operations
- [x] Add richer portfolio and watchlist retrieval flows

### Wave 2 — Market intelligence
- [ ] Add a normalized schema for provider responses
- [ ] Support multiple providers behind the registry
- [ ] Add caching and freshness metadata for market data
- [ ] Add scheduled ingestion jobs for market snapshots

### Wave 3 — Premium experience
- [ ] Add notification and alert delivery primitives
- [ ] Add report generation and export workflows
- [ ] Add usage limits and billing hook scaffolding
- [ ] Add observability, metrics, and health dashboards

### Wave 4 — Scale and compliance
- [ ] Replace SQLite with a managed relational database
- [ ] Add migrations and backup strategy
- [ ] Add API rate limiting and security hardening
- [ ] Add compliance-ready audit and retention policies
