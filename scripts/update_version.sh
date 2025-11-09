#!/bin/bash
# ============================================================
# Version Update Script
# Usage: ./scripts/update_version.sh <new_version>
# Example: ./scripts/update_version.sh 0.4.0
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check arguments
if [ $# -ne 1 ]; then
    echo -e "${RED}Error: Missing version argument${NC}"
    echo "Usage: $0 <new_version>"
    echo "Example: $0 0.4.0"
    exit 1
fi

NEW_VERSION="$1"

# Validate version format (semantic versioning)
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format${NC}"
    echo "Version must follow semantic versioning: MAJOR.MINOR.PATCH"
    echo "Example: 0.4.0, 1.0.0, 2.1.3"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo "unknown")

echo -e "${YELLOW}============================================================${NC}"
echo -e "${YELLOW}Version Update${NC}"
echo -e "${YELLOW}============================================================${NC}"
echo ""
echo -e "Current version: ${GREEN}$CURRENT_VERSION${NC}"
echo -e "New version:     ${GREEN}$NEW_VERSION${NC}"
echo ""

# Confirm
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Aborted.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Updating version to $NEW_VERSION...${NC}"
echo ""

# Update VERSION file
echo "$NEW_VERSION" > "$PROJECT_ROOT/VERSION"
echo -e "${GREEN}✓${NC} Updated VERSION file"

# Update README.md
sed -i.bak "s/version-[0-9]\+\.[0-9]\+\.[0-9]\+/version-$NEW_VERSION/g" "$PROJECT_ROOT/README.md"
rm -f "$PROJECT_ROOT/README.md.bak"
echo -e "${GREEN}✓${NC} Updated README.md"

# Update ARCHITECTURE.md
sed -i.bak "s/v[0-9]\+\.[0-9]\+\.[0-9]\+/v$NEW_VERSION/g" "$PROJECT_ROOT/docs/ARCHITECTURE.md"
rm -f "$PROJECT_ROOT/docs/ARCHITECTURE.md.bak"
echo -e "${GREEN}✓${NC} Updated docs/ARCHITECTURE.md"

# Update ROADMAP.md
sed -i.bak "s/(v[0-9]\+\.[0-9]\+\.[0-9]\+)/(v$NEW_VERSION)/g" "$PROJECT_ROOT/docs/ROADMAP.md"
rm -f "$PROJECT_ROOT/docs/ROADMAP.md.bak"
echo -e "${GREEN}✓${NC} Updated docs/ROADMAP.md"

# Update Dockerfile
sed -i.bak "s/Version: [0-9]\+\.[0-9]\+\.[0-9]\+/Version: $NEW_VERSION/g" "$PROJECT_ROOT/Dockerfile"
sed -i.bak "s/version=\"[0-9]\+\.[0-9]\+\.[0-9]\+\"/version=\"$NEW_VERSION\"/g" "$PROJECT_ROOT/Dockerfile"
rm -f "$PROJECT_ROOT/Dockerfile.bak"
echo -e "${GREEN}✓${NC} Updated Dockerfile"

# Update docker-compose.yml
sed -i.bak "s/Version: [0-9]\+\.[0-9]\+\.[0-9]\+/Version: $NEW_VERSION/g" "$PROJECT_ROOT/docker-compose.yml"
sed -i.bak "s/augment-lite-mcp:[0-9]\+\.[0-9]\+\.[0-9]\+/augment-lite-mcp:$NEW_VERSION/g" "$PROJECT_ROOT/docker-compose.yml"
rm -f "$PROJECT_ROOT/docker-compose.yml.bak"
echo -e "${GREEN}✓${NC} Updated docker-compose.yml"

# Update Makefile
sed -i.bak "s/VERSION := [0-9]\+\.[0-9]\+\.[0-9]\+/VERSION := $NEW_VERSION/g" "$PROJECT_ROOT/Makefile"
sed -i.bak "s/Version: [0-9]\+\.[0-9]\+\.[0-9]\+/Version: $NEW_VERSION/g" "$PROJECT_ROOT/Makefile"
rm -f "$PROJECT_ROOT/Makefile.bak"
echo -e "${GREEN}✓${NC} Updated Makefile"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}Version updated successfully!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Update ${YELLOW}CHANGELOG.md${NC} with changes for v$NEW_VERSION"
echo -e "  2. Review all changes: ${YELLOW}git diff${NC}"
echo -e "  3. Commit changes: ${YELLOW}git add . && git commit -m \"Bump version to $NEW_VERSION\"${NC}"
echo -e "  4. Create tag: ${YELLOW}git tag -a v$NEW_VERSION -m \"Release v$NEW_VERSION\"${NC}"
echo -e "  5. Push changes: ${YELLOW}git push && git push --tags${NC}"
echo ""

