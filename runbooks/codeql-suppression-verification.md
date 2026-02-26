# Runbook: CodeQL Suppression Verification
## Purpose: Verify PayFast MD5 suppression works with CodeQL v4

## Prerequisites
- CodeQL CLI installed: https://codeql.github.com/docs/codeql-cli/getting-started-with-the-codeql-cli/
- Local copy of repository

## Steps

### 1. Create CodeQL database
```bash
codeql database create /tmp/vaal-db --language=javascript --source-root=./server
```

### 2. Run analysis with our config
```bash
codeql database analyze /tmp/vaal-db \
  --format=codeql \
  --output=/tmp/results.bqrs \
  .github/codeql/codeql-config.yml
```

### 3. Convert results to SARIF
```bash
codeql query convert /tmp/results.bqrs --format=sarif --output=/tmp/results.sarif
```

### 4. Check for FIND-001 alert
```bash
jq '.runs[0].results[] | select(.ruleId == "js/insufficient-password-hash")' /tmp/results.sarif
```

## Expected Result
- 0 results for js/insufficient-password-hash in server/server.js
- Suppression comment recognized by CodeQL v4

## Failure Response
If alert still appears:
1. Verify suppression comment is on line IMMEDIATELY before crypto.createHash
2. Ensure no blank lines between comment and code
3. Confirm comment format: `// codeql[js/insufficient-password-hash] ...`
4. Retry analysis

## APEX Compliance
- Linked to: FIND-001
- Owner: @security-team
- Expiry: 2027-Q1
