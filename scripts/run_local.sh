#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if ! command -v uv >/dev/null 2>&1; then
  printf 'Missing uv. Install uv, then run: uv sync\n' >&2
  exit 1
fi

if [[ -z "${TYPESAFE_API_KEY:-}" ]]; then
  printf 'TypeSafe Jev API key (input hidden; not saved): '
  IFS= read -r -s TYPESAFE_API_KEY
  printf '\n'
fi
if [[ -z "$TYPESAFE_API_KEY" ]]; then
  printf 'No API key entered. Server not started.\n' >&2
  exit 1
fi

export TYPESAFE_API_KEY
export PYTHONPATH="$project_root/backend"
printf 'Starting SignaLens API on 127.0.0.1:8765. The key remains in this process only.\n'
exec uv run uvicorn signalens.main:app --host 127.0.0.1 --port 8765 --no-access-log

