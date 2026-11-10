#!/usr/bin/env bash
# Preserve SEO publication/rank commits when other automations update main.
# Never force-push or discard a conflicting update.
set -euo pipefail
for attempt in 1 2 3; do
  if git push origin HEAD:main; then
    echo "PASS: committed SEO update pushed to main"
    exit 0
  fi
  if [[ "$attempt" -eq 3 ]]; then
    echo "::error::Could not push SEO update after three attempts; saved workflow artifact may contain the measurements." >&2
    exit 1
  fi
  echo "::warning::main changed or push was rejected; synchronizing before retry"
  git fetch origin main
  if ! git rebase origin/main; then
    git rebase --abort || true
    echo "::error::SEO update conflicts with upstream main. No force push was attempted." >&2
    exit 1
  fi
  sleep 2
done
