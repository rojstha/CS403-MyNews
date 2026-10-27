#!/bin/bash
# Install (or reinstall) the hourly AI worker for the current macOS user.
# Usage:  bash backend/deploy/mac/install_ai_worker.sh            install
#         bash backend/deploy/mac/install_ai_worker.sh uninstall  remove
set -eu
LABEL="edu.cs403.mynews.aiworker"
BACKEND="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
if [ "${1:-}" = "uninstall" ]; then
  rm -f "$TARGET"
  echo "Removed $LABEL"
  exit 0
fi

[ -f "$BACKEND/.env" ] || { echo "Missing $BACKEND/.env (copy .env.example and fill it in)"; exit 1; }
mkdir -p "$HOME/Library/LaunchAgents" "$BACKEND/logs"
sed "s|__BACKEND__|$BACKEND|g" "$BACKEND/deploy/mac/$LABEL.plist" > "$TARGET"
launchctl bootstrap "gui/$(id -u)" "$TARGET"
echo "Installed $LABEL: runs at minute 5 of every hour. Log: $BACKEND/logs/ai_worker.log"
echo "Run once now with:  launchctl kickstart gui/$(id -u)/$LABEL"
