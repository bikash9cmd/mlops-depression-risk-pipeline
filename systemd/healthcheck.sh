#!/usr/bin/env bash
#
# healthcheck.sh - quick smoke test for all stack components. Intended
# to be run manually or wired into a cron job / systemd timer that
# alerts (e.g. via mail or a webhook) on non-zero exit.
#
# Usage: ./healthcheck.sh

set -uo pipefail

FAILURES=0

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then
        echo "[OK]   $name"
    else
        echo "[FAIL] $name"
        FAILURES=$((FAILURES + 1))
    fi
}

check "API /health endpoint"      "curl -sf http://localhost:8000/health"
check "Airflow webserver"         "curl -sf http://localhost:8080/health"
check "Prometheus"                "curl -sf http://localhost:9090/-/healthy"
check "Grafana"                   "curl -sf http://localhost:3000/api/health"
check "MariaDB container running" "docker inspect -f '{{.State.Running}}' mlops_mariadb | grep -q true"
check "Redis container running"   "docker inspect -f '{{.State.Running}}' mlops_redis | grep -q true"
check "Redis responds to PING"    "docker exec mlops_redis redis-cli ping | grep -q PONG"

echo "----------------------------------------"
if [[ $FAILURES -eq 0 ]]; then
    echo "All checks passed."
    exit 0
else
    echo "$FAILURES check(s) failed."
    exit 1
fi
