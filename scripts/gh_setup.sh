#!/usr/bin/env bash
set -euo pipefail
if ! command -v gh >/dev/null; then echo "Install gh CLI"; exit 1; fi
if [[ $# -lt 1 ]]; then echo "Usage: $0 owner/repo [topics...]"; exit 1; fi
REPO="$1"; shift || true
TOPICS=("$@")
gh api -X PUT repos/$REPO/actions/permissions -f enabled=true || true
gh api -X PUT repos/$REPO/branches/main/protection   -H "Accept: application/vnd.github+json"   --input branch_protection.json
if [[ ${#TOPICS[@]} -gt 0 ]]; then
  gh repo edit $REPO $(printf -- "--add-topic %s " "${TOPICS[@]}")
fi
echo "Now add secrets with: gh secret set NAME -R $REPO -b"$VALUE""
