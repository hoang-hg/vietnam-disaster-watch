#!/bin/sh
# PostgreSQL Backup Script for Vietnam Disaster Watch
# Runs daily, keeps last 7 days of backups

set -e

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/viet_disaster_backup_$DATE.sql"

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

echo "[$(date)] Starting database backup..."

# Perform backup
pg_dump -h db -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE
echo "[$(date)] Backup completed: ${BACKUP_FILE}.gz"

# Get file size
SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
echo "[$(date)] Backup size: $SIZE"

# Delete backups older than 7 days
echo "[$(date)] Cleaning old backups (keeping last 7 days)..."
find $BACKUP_DIR -name "viet_disaster_backup_*.sql.gz" -mtime +7 -delete

# Count remaining backups
COUNT=$(find $BACKUP_DIR -name "viet_disaster_backup_*.sql.gz" | wc -l)
echo "[$(date)] Total backups: $COUNT"

echo "[$(date)] Backup process completed successfully"
