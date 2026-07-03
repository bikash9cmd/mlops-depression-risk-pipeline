#!/usr/bin/env bash
#
# backup_db.sh - dumps the MariaDB database to a timestamped, gzipped
# SQL file. Intended to be run via a daily cron entry on the host:
#
#   0 2 * * * /opt/mlops-depression-risk-pipeline/scripts/backup_db.sh
#
# Keeps the last 14 days of backups and prunes anything older.

set -euo pipefail

BACKUP_DIR="/opt/mlops-depression-risk-pipeline/backups"
CONTAINER="mlops_mariadb"
RETENTION_DAYS=14

source "$(dirname "$0")/../.env"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_FILE="$BACKUP_DIR/depression_pipeline_${TIMESTAMP}.sql.gz"

echo "Dumping database from container $CONTAINER..."
docker exec "$CONTAINER" mysqldump \
    -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" \
    | gzip > "$OUT_FILE"

echo "Backup written to $OUT_FILE"

echo "Pruning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "Done."
