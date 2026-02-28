# Runbook: Rate Limit Load Test
## Purpose: Verify payment endpoint rate limiting works correctly

## Prerequisites
- Artillery installed: `npm install -g artillery`
- Valid test authentication token
- Staging environment URL

## Steps

### 1. Run load test
```bash
artillery run --variables '{
  "endpoint": "/api/payment/process",
  "token": "valid-test-token",
  "payload": {"amount": 100, "plan": "basic"}
}' tests/load/payment-rate-limit.yml
```

### 2. Monitor responses
- First 50 requests: HTTP 200
- Requests 51+: HTTP 429 with Retry-After header

### 3. Verify per-user isolation
```bash
# Run same test with different token
# Confirm User B can still make requests when User A is rate limited
```

## Expected Result
- 429 response after 50th request in 15min window
- Retry-After header present in 429 response
- Per-user limits work independently

## Failure Response
If rate limiting not working:
1. Check express-rate-limit middleware is applied to route
2. Verify keyGenerator returns unique key per user/IP
3. Confirm windowMs and max values are correct
4. Check for middleware ordering issues (must be after authenticate)

## APEX Compliance
- Linked to: FIX-002
- Owner: @security-team
- Validation: Required before merge
