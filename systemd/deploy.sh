#!/usr/bin/env bash
#
# deploy.sh - pull latest code, rebuild images, and restart the stack
# via systemd on a Linux host. Meant to be run on the server itself
# (or via SSH from CI), not inside a container.
#
# Usage: sudo ./deploy.sh

set -euo pipefail

APP_DIR="/opt/mlops-depression-risk-pipeline"
SERVICE_NAME="mlops-stack"
LOG_FILE="/var/log/mlops-deploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

log "Starting deployment"

cd "$APP_DIR"

log "Pulling latest changes from git"
git pull origin main

log "Rebuilding Docker images"
docker compose build --pull

log "Restarting stack via systemd"
systemctl restart "$SERVICE_NAME"

log "Waiting for containers to report healthy"
sleep 15
docker compose ps

log "Deployment finished"
