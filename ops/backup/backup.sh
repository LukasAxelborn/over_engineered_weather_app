#!/bin/sh
# Postgres logical backup with simple retention. Intended to run inside the
# `backup` container (postgres image) via Ofelia, or manually.
set -eu

: "${POSTGRES_USER:?POSTGRES_USER required}"
: "${POSTGRES_DB:?POSTGRES_DB required}"
export PGPASSWORD="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"
PGHOST="${PGHOST:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION="${BACKUP_RETENTION:-14}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/weather-$STAMP.sql.gz"

echo "[backup] dumping $POSTGRES_DB from $PGHOST -> $OUT"
pg_dump -h "$PGHOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$OUT"

echo "[backup] pruning older than last $RETENTION files"
ls -1t "$BACKUP_DIR"/weather-*.sql.gz 2>/dev/null | tail -n +"$((RETENTION + 1))" | xargs -r rm -f

echo "[backup] done: $(du -h "$OUT" | cut -f1)"
