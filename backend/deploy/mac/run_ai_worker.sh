#!/bin/bash
# One AI-worker pass: generate summaries for stories whose inputs changed and
# save them to the shared database. Run hourly by launchd (install_ai_worker.sh).
# Settings, including the Neon DATABASE_URL, come from backend/.env (git-ignored).
set -u
BACKEND="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$BACKEND" || exit 1
mkdir -p logs
LOG="$BACKEND/logs/ai_worker.log"

# Ollama runs as a Homebrew background service; give it time after login/wake.
for _ in $(seq 1 15); do
  curl -sf http://localhost:11434/api/version >/dev/null && break
  sleep 2
done

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) AI worker start" >> "$LOG"
"$BACKEND/.venv/bin/python" -m app.ai_worker >> "$LOG" 2>&1
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) exit $?" >> "$LOG"
