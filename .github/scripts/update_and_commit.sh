#!/bin/bash
set -e

# Script to update stream URLs and commit changes if any
# Usage: ./update_and_commit.sh --url <URL> --file <FILE> --entry-name <NAME> [OPTIONS]

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the repository root directory (3 levels up from .github/scripts/)
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_PATH="$REPO_ROOT/.venv"

# Change to repository root to ensure git commands work
cd "$REPO_ROOT"

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    echo -e "${YELLOW}Warning: .venv not found at $VENV_PATH${NC}"
    echo "Using system Python"
fi

# Parse arguments and pass them to the Python script
echo "Running stream updater..."
python "$(dirname "$0")/update_streams.py" "$@"
PYTHON_EXIT_CODE=$?

# Check if Python script failed
if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}✗ Stream updater failed with exit code $PYTHON_EXIT_CODE${NC}"
    exit $PYTHON_EXIT_CODE
fi

echo ""
echo "Checking for git changes..."

# Extract the file path from arguments
FILE_PATH=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --file)
            FILE_PATH="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Check if file path was provided
if [ -z "$FILE_PATH" ]; then
    echo -e "${RED}✗ Could not determine file path from arguments${NC}"
    exit 1
fi

# Check if there are any changes
if git diff --quiet "$FILE_PATH"; then
    echo -e "${GREEN}✓ No changes detected - playlist is up to date${NC}"
    exit 0
fi

echo -e "${YELLOW}Changes detected in $FILE_PATH${NC}"
echo ""
echo "Git diff:"
git diff "$FILE_PATH"
echo ""

# Configure git if not already configured
if [ -z "$(git config user.name)" ]; then
    echo "Configuring git user..."
    git config user.name "Stream Updater Bot"
    git config user.email "stream-updater-bot@armany.ir"
fi

# Stage the changes
echo "Staging changes..."
git add "$FILE_PATH"

# Commit the changes
COMMIT_MESSAGE="chore: update stream URLs [automated]"
echo "Committing changes..."
git commit -m "$COMMIT_MESSAGE"

# Try to push the changes
echo "Pushing changes to remote..."
if git push; then
    echo -e "${GREEN}✓ Successfully pushed changes${NC}"
else
    echo -e "${RED}✗ Failed to push changes${NC}"
    echo "You may need to pull first or check your permissions"
    exit 1
fi

echo -e "${GREEN}✓ Update completed successfully${NC}"
