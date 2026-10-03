# Feature: API Rate Limiting

## Problem Statement

The `/api/users` and `/api/orders` endpoints have no rate limiting, leaving the service
vulnerable to abuse and resource exhaustion. During a recent load spike, a single client
made 50,000 requests in 2 minutes, degrading performance for all users.

## Requirements

### Functional

- [ ] Rate limit all `/api/*` endpoints per API key
- [ ] Default limit: 100 requests per minute per API key
- [ ] Return `429 Too Many Requests` with `Retry-After` header when limit exceeded
- [ ] Admin API keys get 1,000 requests per minute
- [ ] Rate limit configuration stored in database, editable via admin panel

### Non-Functional

- [ ] Rate check adds less than 5ms latency per request (p99)
- [ ] Rate limiter survives server restarts (use Redis, not in-memory)
- [ ] Graceful degradation: if Redis is unavailable, allow requests through with logging

## Constraints

- Must use existing Redis cluster (redis-prod-01, port 6379)
- Must not require API consumers to change their integration
- Express.js middleware pattern for consistency with existing auth middleware
- TypeScript with strict mode

## Acceptance Criteria

- [ ] Requests within limit return normal responses with `X-RateLimit-Remaining` header
- [ ] Request 101 within a 1-minute window returns 429 with correct `Retry-After` value
- [ ] Admin keys confirmed to have 1,000/min limit
- [ ] Rate limit resets correctly after the window expires
- [ ] Redis failure does not cause 500 errors (graceful fallback)
- [ ] Load test confirms less than 5ms p99 latency overhead

## Out of Scope

- Per-endpoint rate limits (all endpoints share the same limit for now)
- IP-based rate limiting (only API key-based)
- Rate limit dashboard or analytics
