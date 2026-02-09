#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="outputs"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "No outputs/ directory found. Nothing to process."
  exit 0
fi

conflict_files=$(rg -l "^(<<<<<<<|>>>>>>>)" "$TARGET_DIR" || true)

if [[ -z "$conflict_files" ]]; then
  echo "No merge conflict markers found in $TARGET_DIR."
  exit 0
fi

echo "Found merge conflict markers in:"
echo "$conflict_files"
echo
echo "Automatic conflict resolution is not safe for arbitrary files."
echo "Please resolve conflicts manually in the files listed above."
exit 1
