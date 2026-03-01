# 🔧 CodeQL Branch Protection Fix Required

## Issue
GitHub shows "CodeQL 3 configurations not found" because the branch protection rules still reference the old matrix-based CodeQL workflow.

## Root Cause
The previous workflow used a matrix strategy that created 3 separate configurations:
- `CodeQL (javascript)`
- `CodeQL (python)`
- `CodeQL (matrix)`

The new workflow (security.yml) uses a single job that analyzes both languages together:
- `Security Scanning / CodeQL Analysis`

## Fix Steps (Repository Admin Required)

### Step 1: Navigate to Branch Protection
1. Go to: https://github.com/deedk822-lang/vaal-ai-empire-site/settings/branches
2. Find: `digital-preeminence-fixes` branch protection rule
3. Click: `Edit`

### Step 2: Update Required Status Checks
**REMOVE these old checks:**
- ❌ `Code scanning results / CodeQL`
- ❌ Any check with `CodeQL` and matrix indicators

**ADD this new check:**
- ✅ `Security Scanning / CodeQL Analysis`

### Step 3: Save Changes
1. Scroll down and click `Save changes`
2. Re-run the workflow or push a new commit to verify

## Verification
After the fix, the PR should show:
- ✅ `Security Scanning / CodeQL Analysis` (instead of "3 configurations not found")
- ✅ All 62 checks passing

## Current Status (59/62 passing)
The 3 "not found" configurations are the only blockers. All actual security scans pass:
- ✅ Bandit — No new alerts
- ✅ npm audit — Clean
- ✅ Safety — Clean
- ✅ Detect Secrets — Clean

## Affected PR
- PR #117: https://github.com/deedk822-lang/vaal-ai-empire-site/pull/117
