#!/bin/bash
#
# fix-conflicts.sh - Detect and optionally resolve Git merge conflicts
#
# Usage:
#   ./fix-conflicts.sh [--strip] [--dry-run] [--backup-dir DIR]
#
# Options:
#   --strip       Automatically strip conflict markers (keeps "ours" side)
#   --dry-run     Show what would be done without making changes
#   --backup-dir  Directory to store backups (default: ./conflict-backups)
#
# This script detects Git merge conflict markers in files and can optionally
# strip them. By default, it only detects conflicts without modifying files.
#

set -euo pipefail

# Configuration
STRIP_MODE=false
DRY_RUN=false
BACKUP_DIR="./conflict-backups"
FILES_PROCESSED=0
CONFLICTS_FOUND=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --strip)
            STRIP_MODE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--strip] [--dry-run] [--backup-dir DIR]"
            echo ""
            echo "Options:"
            echo "  --strip       Automatically strip conflict markers (keeps 'ours' side)"
            echo "  --dry-run     Show what would be done without making changes"
            echo "  --backup-dir  Directory to store backups (default: ./conflict-backups)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Conflict patterns - only standard Git conflict markers
# Note: We intentionally do NOT include branch-name patterns as they cause
# false positives (e.g., matching MIME types like "text/html", import paths,
# or legitimate content that matches the pattern)
CONFLICT_PATTERNS=(
    '^<<<<<<< '          # Git conflict start
    '^=======$'          # Git conflict separator
    '^>>>>>>> '          # Git conflict end
)

# Function to check if a file has conflicts
check_file_for_conflicts() {
    local file="$1"
    local has_conflict=false
    local line_num=0
    local conflict_lines=()

    while IFS= read -r line || [[ -n "$line" ]]; do
        ((line_num++))
        for pattern in "${CONFLICT_PATTERNS[@]}"; do
            if [[ "$line" =~ $pattern ]]; then
                has_conflict=true
                conflict_lines+=("$line_num: $line")
            fi
        done
    done < "$file"

    if [[ "$has_conflict" == true ]]; then
        echo -e "${YELLOW}Conflict found in: $file${NC}"
        for conflict_line in "${conflict_lines[@]}"; do
            echo "  Line $conflict_line"
        done
        return 0
    fi
    return 1
}

# Function to strip conflicts from a file (keeps "ours" side)
strip_conflicts_from_file() {
    local file="$1"
    local backup_path="$BACKUP_DIR/$(basename "$file").bak"
    local temp_file=$(mktemp)
    local in_conflict=false
    local conflict_start_line=0
    local line_num=0
    local changes_made=false

    # Create backup
    mkdir -p "$BACKUP_DIR"
    cp "$file" "$backup_path"

    while IFS= read -r line || [[ -n "$line" ]]; do
        ((line_num++))
        
        if [[ "$line" =~ ^'<<<<<<< ' ]]; then
            in_conflict=true
            conflict_start_line=$line_num
            changes_made=true
            continue
        elif [[ "$line" =~ ^'=======$' ]]; then
            # Skip the separator line
            continue
        elif [[ "$line" =~ ^'>>>>>>> ' ]]; then
            in_conflict=false
            continue
        fi
        
        # Only output lines that are not part of "theirs" section
        if [[ "$in_conflict" == true ]]; then
            # We're in the conflict, but before =======, so this is "ours"
            echo "$line" >> "$temp_file"
        else
            echo "$line" >> "$temp_file"
        fi
    done < "$file"

    if [[ "$changes_made" == true ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            echo -e "${BLUE}Would strip conflicts from: $file${NC}"
        else
            mv "$temp_file" "$file"
            echo -e "${GREEN}Stripped conflicts from: $file (backup: $backup_path)${NC}"
        fi
    else
        rm -f "$temp_file"
    fi
}

# Main logic
echo -e "${BLUE}=== Git Conflict Detection ===${NC}"
echo ""

# Check if we're in a Git repository
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo -e "${RED}Error: Not in a Git repository${NC}"
    exit 1
fi

# Find files to check (exclude .git directory and node_modules)
echo "Scanning for conflict markers..."
echo ""

# Get list of tracked files
while IFS= read -r -d '' file; do
    # Skip binary files, .git, node_modules, etc.
    if [[ "$file" == *".git"* ]] || \
       [[ "$file" == *"node_modules"* ]] || \
       [[ "$file" == *".png" ]] || \
       [[ "$file" == *".jpg" ]] || \
       [[ "$file" == *".jpeg" ]] || \
       [[ "$file" == *".gif" ]] || \
       [[ "$file" == *".ico" ]] || \
       [[ "$file" == *".woff"* ]] || \
       [[ "$file" == *".ttf" ]] || \
       [[ "$file" == *".eot" ]] || \
       [[ "$file" == *".pdf" ]]; then
        continue
    fi
    
    ((FILES_PROCESSED++))
    
    if check_file_for_conflicts "$file"; then
        ((CONFLICTS_FOUND++))
        
        if [[ "$STRIP_MODE" == true ]]; then
            strip_conflicts_from_file "$file"
        fi
    fi
done < <(git ls-files -z 2>/dev/null || find . -type f -not -path "./.git/*" -print0)

echo ""
echo -e "${BLUE}=== Summary ===${NC}"
echo "Files processed: $FILES_PROCESSED"
echo -e "Conflicts found: ${CONFLICTS_FOUND}"

if [[ "$CONFLICTS_FOUND" -gt 0 ]]; then
    if [[ "$STRIP_MODE" == true ]]; then
        echo -e "${GREEN}Conflicts have been processed. Backups stored in: $BACKUP_DIR${NC}"
    else
        echo -e "${YELLOW}Run with --strip to automatically resolve conflicts.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}No conflicts found.${NC}"
fi

exit 0
