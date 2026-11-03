#!/bin/bash
# Install the ECC (Everything Claude Code) plugin in Claude Code cloud sessions.
# Project settings enable ecc@ecc, but cloud containers start without it installed.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

MARKETPLACE_NAME="ecc"
MARKETPLACE_SOURCE="affaan-m/ECC"
PLUGIN="ecc@ecc"

if ! command -v claude >/dev/null 2>&1; then
  echo "session-start: claude CLI not found, skipping ECC install" >&2
  exit 0
fi

if claude plugin list 2>/dev/null | grep -q "$PLUGIN"; then
  exit 0
fi

if ! claude plugin marketplace list 2>/dev/null | grep -qw "$MARKETPLACE_NAME"; then
  claude plugin marketplace add "$MARKETPLACE_SOURCE"
fi

claude plugin install "$PLUGIN"
