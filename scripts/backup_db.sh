#!/bin/bash
# Database backup script
# Usage: ./scripts/backup_db.sh

set -e

BACKUP_DIR="/opt/backups/moder_bpm_prime"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/moder_bpm_prime_$DATE.sql.gz"

# Load environment
source /opt/moder_bpm_prime/.env

echo "🗄 Creating database backup..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
docker exec moder_bpm_prime-bot-1 pg_dump $DATABASE_URL | gzip > $BACKUP_FILE

echo "✅ Backup created: $BACKUP_FILE"

# Keep only last 7 days
find $BACKUP_DIR -name "moder_bpm_prime_*.sql.gz" -mtime +7 -delete

echo "🧹 Old backups cleaned up"

# Optional: Upload to cloud storage (uncomment and configure)
# aws s3 cp $BACKUP_FILE s3://your-bucket/backups/
# rclone copy $BACKUP_FILE gdrive:backups/