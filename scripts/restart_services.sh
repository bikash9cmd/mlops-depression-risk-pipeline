#!/usr/bin/env bash
#
# restart_services.sh - restart one or more containers in the stack
# without tearing the whole thing down. Handy after editing a DAG or
# swapping in a new model file.
#
# Usage:
#   ./restart_services.sh api
#   ./restart_services.sh api airflow-scheduler
#   ./restart_services.sh          (restarts everything)

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -eq 0 ]]; then
    echo "No service specified, restarting full stack..."
    docker compose restart
else
    for svc in "$@"; do
        echo "Restarting $svc..."
        docker compose restart "$svc"
    done
fi

docker compose ps
