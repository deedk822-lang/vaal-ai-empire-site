# CodeQL setup model

This repository now uses a **single-config, repository-managed CodeQL model**:

- Authoritative workflow: `.github/workflows/codeql.yml`
- Authoritative config: `.github/codeql/codeql-config.yml`

If GitHub Security UI shows **"3 configurations"**, that value is from GitHub's
**Code scanning setup state in repository settings** (Advanced setup metadata), not
from files in this repository.

## Required repository setting alignment

In GitHub repository settings (`Security & analysis` → `Code scanning`), remove any
stale Advanced setup configuration entries that reference older workflow/config files
so only the workflow-defined model remains active.
