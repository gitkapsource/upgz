#!/bin/bash

DB_NAME="kamailio"
DB_USER="kamailio"
DB_PASS="kamailiorw"

BACKUP_DIR="/gozupees/db-backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILE_NAME="${DB_NAME}_${TIMESTAMP}.sql.gz"

mkdir -p $BACKUP_DIR

# Backup
/usr/bin/mysqldump -u $DB_USER -p$DB_PASS $DB_NAME | gzip > "$BACKUP_DIR/$FILE_NAME"

# Delete backups older than 7 days
find $BACKUP_DIR -type f -name "*.gz" -mtime +7 -delete

echo "Backup created: $BACKUP_DIR/$FILE_NAME"
echo "Old backups cleaned."
