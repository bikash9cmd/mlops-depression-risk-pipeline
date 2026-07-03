#!/usr/bin/env bash
#
# logs.sh - convenience wrapper for tailing logs of a given service,
# or all of them at once. Saves typing the full docker compose command.
#
# Usage:
#   ./logs.sh api
#   ./logs.sh              (tails everything)

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -eq 0 ]]; then
    docker compose logs -f --tail=200
else
    docker compose logs -f --tail=200 "$1"
fi
