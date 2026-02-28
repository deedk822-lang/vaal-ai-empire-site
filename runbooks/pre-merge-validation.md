# Runbook: Pre-Merge Validation
## Purpose: Final validation before merging PR #128

## Mandatory Checks (All Must Pass)

### [ ] 1. Repository Secrets Configuration
```bash
gh secret list --repo deedk822-lang/vaal-ai-empire-site
```
**Expected:** OLLAMA_API_KEY present and marked as "Selected"  
**If missing:** `gh secret set OLLAMA_API_KEY --repo deedk822-lang/vaal-ai-empire-site`

### [ ] 2. Staging PayFast Integration Test
```bash
curl -X POST https://staging.vaal-ai.com/payfast/itn \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "test_data=validated&signature=test"
```
**Expected:** 200 response with sanitized log entry (no raw passphrase)  
**Verify:** Log entry contains "_" not control characters

### [ ] 3. Rate Limit Threshold Validation
**Action:** Review payment volume analytics in Grafana  
**Command:** `grafana-cli dashboards get-payment-metrics --from=now-7d`  
**Expected:** Peak legitimate traffic < 40 req/15min per user  
**If >40:** Adjust rate limit or implement burst allowance

### [ ] 4. Secret Rotation Verification
```bash
gh secret set PAYFAST_MERCHANT_KEY --repo deedk822-lang/vaal-ai-empire-site
```
**Expected:** New key value accepted; old key invalidated in PayFast dashboard  
**Verify:** Integration tests pass with new key

### [ ] 5. Branch Protection Rule Confirmation
**Action:** GitHub Settings → Branches → main → Edit branch protection  
**Expected:** "Require status checks to pass before merging" enabled  
**Expected:** "CodeQL Analysis" check selected as required  
**If not:** Enable and save

## Post-Merge Monitoring (First 24 Hours)

### [ ] 6. Payment Endpoint Metrics
**Dashboard:** Grafana → Payment Performance  
**Alert:** P95 latency > 500ms or error rate > 1%  
**Response:** Rollback via git revert if thresholds exceeded

### [ ] 7. Rate Limit Alert Monitoring
**SIEM Query:** `index=alerts event=payment_endpoint_429_rate`  
**Expected:** < 5 legitimate triggers/hour  
**If >5:** Investigate for abuse or adjust threshold

### [ ] 8. CodeQL Alert Monitoring
**GitHub Security Tab → CodeQL → optimal-performance branch**  
**Expected:** 0 new alerts for 24 hours  
**If alerts appear:** Review and apply APEX suppression protocol if false positive

## Rollback Procedure (If Needed)
```bash
git checkout main
git revert <merge-commit-sha> -m "Revert PR #128: APEX validation failure"
git push origin main
```
**Notify:** #security-alerts Slack channel  
**Document:** Incident report in JIRA-SEC-XXXX

## APEX Compliance
- Linked to: All FINDs
- Owner: @security-team
- Required for: PR merge authorization
