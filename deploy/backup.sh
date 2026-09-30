#!/bin/sh
# Nightly Postgres backup (cron: 0 2 * * *  /path/deploy/backup.sh). Managed databases also offer automatic backups; use both.
set -e
STAMP=$(date +%Y%m%d-%H%M)
OUT=${BACKUP_DIR:-/var/backups/debut}/debut-$STAMP.sql.gz
mkdir -p "$(dirname "$OUT")"
pg_dump "$DATABASE_URL_PLAIN" | gzip > "$OUT"       # DATABASE_URL_PLAIN=postgresql://user:pass@host/db
[ -n "$S3_BACKUP_URI" ] && aws s3 cp "$OUT" "$S3_BACKUP_URI/"
find "$(dirname "$OUT")" -name 'debut-*.sql.gz' -mtime +14 -delete
echo "backup ok: $OUT"
