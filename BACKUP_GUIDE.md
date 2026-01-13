# Database Backup System

## Overview
Automated daily PostgreSQL backups for Vietnam Disaster Watch system.

## Configuration

### Backup Schedule
- **Frequency**: Every 24 hours
- **Time**: Runs continuously (starts immediately on container start)
- **Retention**: Last 7 days (older backups auto-deleted)

### Backup Location
- **Container**: `/backups`
- **Host**: `./backups` (mapped to project root)

## File Format
```
viet_disaster_backup_YYYYMMDD_HHMMSS.sql.gz
```

Example: `viet_disaster_backup_20260107_020000.sql.gz`

## Storage Requirements
- **Average backup size**: ~5-10 MB (compressed)
- **Max storage (7 days)**: ~70 MB
- **Compression**: gzip

## Manual Backup

### Create Immediate Backup
```bash
# Access backup container
docker exec -it viet_disaster_backup sh

# Run backup script manually
/backup.sh
```

### List Backups
```bash
ls -lh ./backups
```

### Check Backup Logs
```bash
docker logs viet_disaster_backup
```

## Restore from Backup

### 1. Stop the Application
```bash
docker-compose -f docker-compose.prod.yml down
```

### 2. Start Only Database
```bash
docker-compose -f docker-compose.prod.yml up -d db
```

### 3. Restore Database
```bash
# Replace YYYYMMDD_HHMMSS with actual backup timestamp
BACKUP_FILE="viet_disaster_backup_20260107_020000.sql.gz"

# Decompress and restore
gunzip -c ./backups/$BACKUP_FILE | docker exec -i viet_disaster_db psql -U postgres -d viet_disaster
```

### 4. Restart All Services
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Backup Verification

### Test Backup Integrity
```bash
# Decompress without extracting
gunzip -t ./backups/viet_disaster_backup_*.sql.gz

# Check SQL file is valid
gunzip -c ./backups/viet_disaster_backup_*.sql.gz | head -n 20
```

### Automated Verification (Recommended)
Add to cron for weekly verification:
```bash
0 3 * * 0 cd /path/to/project && ./scripts/verify-backup.sh
```

## Troubleshooting

### Backup Not Running
```bash
# Check container status
docker ps | grep backup

# Check logs
docker logs viet_disaster_backup

# Restart backup service
docker-compose -f docker-compose.prod.yml restart db-backup
```

### Disk Space Issues
```bash
# Check disk usage
du -sh ./backups

# Manual cleanup (remove backups older than 7 days)
find ./backups -name "viet_disaster_backup_*.sql.gz" -mtime +7 -delete
```

### Permission Issues
```bash
# Fix backup directory permissions
chmod 755 ./backups
chmod +x ./scripts/backup-db.sh
```

## Best Practices

### 1. Off-Site Backups
Sync to remote storage daily:
```bash
# Example: AWS S3
aws s3 sync ./backups s3://your-bucket/viet-disaster-backups/

# Example: rsync to remote server
rsync -avz ./backups/ user@backup-server:/backups/viet-disaster/
```

### 2. Test Restores Monthly
```bash
# Create test environment
# Restore backup
# Verify data integrity
```

### 3. Monitor Backup Size
```bash
# Alert if backup size grows significantly
CURRENT_SIZE=$(du -s ./backups | cut -f1)
if [ $CURRENT_SIZE -gt 100000 ]; then
    echo "Warning: Backup size exceeds 100MB"
fi
```

### 4. Encrypt Sensitive Backups
```bash
# Encrypt before uploading
gpg --symmetric --cipher-algo AES256 backup.sql.gz
```

## Configuration Options

### Change Backup Schedule
Edit `docker-compose.prod.yml`:
```yaml
command: >
  sh -c "while true; do
    /backup.sh;
    sleep 43200;  # 12 hours instead of 24
  done"
```

### Change Retention Period
Edit `scripts/backup-db.sh`:
```bash
# Keep last 14 days instead of 7
find $BACKUP_DIR -name "viet_disaster_backup_*.sql.gz" -mtime +14 -delete
```

### Backup to Different Location
```yaml
volumes:
  - /mnt/external/backups:/backups  # External drive
```

## Maintenance

### Weekly Tasks
- [ ] Verify latest backup file exists
- [ ] Check backup logs for errors
- [ ] Confirm disk space < 80%

### Monthly Tasks
- [ ] Test restore procedure
- [ ] Verify backup integrity
- [ ] Review backup size trends

### Quarterly Tasks
- [ ] Test disaster recovery plan
- [ ] Update backup documentation
- [ ] Review retention policy

## Support

For issues or questions:
- Check logs: `docker logs viet_disaster_backup`
- Review script: `cat scripts/backup-db.sh`
- Test manually: `docker exec -it viet_disaster_backup /backup.sh`

---

**Last Updated**: 2026-01-07  
**Backup System Version**: 1.0  
**Status**: ✅ Production Ready
