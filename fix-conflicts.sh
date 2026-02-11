#!/usr/bin/env bash
# Vaal AI Empire - Merge Conflict Detection & Resolution Helper
# Usage: ./fix-conflicts.sh [directory] [--fix]
#   directory: Directory to scan (default: current directory)
#   --fix: Attempt to remove conflict markers (use with caution!)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - parse flags first
FIX_MODE=false
TARGET_DIR="."

# Check for --fix flag and parse arguments
if [[ "${1:-}" == "--fix" ]]; then
    FIX_MODE=true
    TARGET_DIR="${2:-.}"
elif [[ "${2:-}" == "--fix" ]]; then
    FIX_MODE=true
    TARGET_DIR="${1:-.}"
elif [[ -n "${1:-}" && "${1:-}" != "--fix" ]]; then
    TARGET_DIR="$1"
fi

# Ensure target directory exists
if [[ ! -d "$TARGET_DIR" ]]; then
    echo -e "${RED}Error: Directory '$TARGET_DIR' not found${NC}"
    exit 1
fi

echo "🔍 Scanning for merge conflicts in: $TARGET_DIR"
echo ""

# Define conflict patterns
CONFLICT_PATTERNS=(
    '^<<<<<<< '          # Git conflict start
    '^=======$'          # Git conflict separator
    '^>>>>>>> '          # Git conflict end
    '^[a-z-]+/[^/]+$'    # General branch pattern (e.g., feat/name, fix/name)
)

# Find files with conflicts
FOUND_CONFLICTS=false
CONFLICT_FILES=()

# Function to check if a file has conflicts
check_file() {
    local file="$1"
    local has_conflict=false
    
    for pattern in "${CONFLICT_PATTERNS[@]}"; do
        if grep -qE "$pattern" "$file" 2>/dev/null; then
            has_conflict=true
            break
        fi
    done
    
    if $has_conflict; then
        echo "$file"
        return 0
    fi
    return 1
}

export -f check_file
export CONFLICT_PATTERNS

# Find all text files and check for conflicts
echo "Scanning files..."
while IFS= read -r file; do
    if check_file "$file"; then
        FOUND_CONFLICTS=true
        CONFLICT_FILES+=("$file")
    fi
done < <(find "$TARGET_DIR" -type f \
    ! -path '*/node_modules/*' \
    ! -path '*/.git/*' \
    ! -path '*/__pycache__/*' \
    ! -name '*.png' ! -name '*.jpg' ! -name '*.jpeg' \
    ! -name '*.gif' ! -name '*.ico' ! -name '*.svg' \
    ! -name '*.woff' ! -name '*.woff2' ! -name '*.ttf' \
    ! -name '*.eot' ! -name '*.otf' ! -name '*.mp4' \
    ! -name '*.webm' ! -name '*.mp3' ! -name '*.pdf' \
    ! -name '*.zip' ! -name '*.tar.gz' 2>/dev/null)

if ! $FOUND_CONFLICTS; then
    echo -e "${GREEN}✅ No merge conflict markers found!${NC}"
    exit 0
fi

echo ""
echo -e "${RED}❌ Found merge conflicts in the following files:${NC}"
echo ""

for file in "${CONFLICT_FILES[@]}"; do
    echo -e "${YELLOW}  • $file${NC}"
    
    # Show the specific conflict lines
    for pattern in "${CONFLICT_PATTERNS[@]}"; do
        if grep -nE "$pattern" "$file" 2>/dev/null | head -3; then
            echo "    ..."
            break
        fi
    done
    echo ""
done

echo "Total files with conflicts: ${#CONFLICT_FILES[@]}"
echo ""

# If fix mode is enabled, attempt to fix
if $FIX_MODE; then
    echo -e "${YELLOW}⚠️  FIX MODE ENABLED${NC}"
    echo "This will remove conflict markers but may NOT produce correct results!"
    echo "Manual review is strongly recommended after running this."
    echo ""
    
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo "Aborted."
        exit 0
    fi
    
    FIXED_COUNT=0
    for file in "${CONFLICT_FILES[@]}"; do
        echo "Processing: $file"
        
        # Create backup
        cp "$file" "$file.backup"
        
        # Remove conflict markers (naive approach - removes lines with markers)
        # This is NOT a complete solution but helps clean up
        sed -i.bak '/^<<<<<<< /d' "$file"
        sed -i.bak '/^=======$/d' "$file"
        sed -i.bak '/^>>>>>>> /d' "$file"
        
        # Remove .bak files created by sed
        rm -f "$file.bak"
        
        FIXED_COUNT=$((FIXED_COUNT + 1))
    done
    
    echo ""
    echo -e "${GREEN}✅ Processed $FIXED_COUNT files${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Backups created with .backup extension${NC}"
    echo -e "${YELLOW}⚠️  Please review all changes before committing!${NC}"
    
    # Exit successfully after fixing
    exit 0
else
    echo -e "${RED}Please resolve conflicts manually or run with --fix flag (use with caution!)${NC}"
    echo ""
    echo "To attempt automatic cleanup (requires manual review after):"
    echo "  ./fix-conflicts.sh --fix"
fi

exit 1
