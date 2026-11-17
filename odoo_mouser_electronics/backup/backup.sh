#!/bin/bash

set -e

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="/tmp/backup"

mkdir -p "${BACKUP_DIR}"

echo "====================================="
echo "Starting Odoo Backup"
echo "Date: ${DATE}"
echo "Database: ${DB_NAME}"
echo "Host: ${DB_HOST}"
echo "Bucket: ${R2_BUCKET}"
echo "====================================="

echo "Creating database dump..."

export PGPASSWORD="${DB_PASSWORD}"

pg_dump \
  -h "${DB_HOST}" \
  -U "${DB_USER}" \
  -Fc \
  "${DB_NAME}" \
  > "${BACKUP_DIR}/database.dump"

echo "Database dump completed."

echo "Copying filestore..."

FILESTORE_PATH="/var/lib/odoo/filestore/${DB_NAME}"

if [ -d "${FILESTORE_PATH}" ]; then
    mkdir -p "${BACKUP_DIR}/filestore"

    cp -r "${FILESTORE_PATH}" "${BACKUP_DIR}/filestore/"

    echo "Filestore copied successfully for database: ${DB_NAME}"
else
    echo "Filestore not found for database: ${DB_NAME}"
fi

echo "Creating backup archive..."

ARCHIVE_FILE="/tmp/odoo-backup-${DB_NAME}-${DATE}.zip"

(
  cd "${BACKUP_DIR}"
  zip -r "${ARCHIVE_FILE}" .
)

echo "Archive created: ${ARCHIVE_FILE}"

echo "Configuring R2..."

mkdir -p ~/.config/rclone

cat > ~/.config/rclone/rclone.conf <<EOF
[r2]
type = s3
provider = Cloudflare
access_key_id = ${R2_ACCESS_KEY}
secret_access_key = ${R2_SECRET_KEY}
endpoint = https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com
acl = private
no_check_bucket = true
EOF

echo "Testing R2 connection..."

rclone lsd "r2:${R2_BUCKET}" >/dev/null

echo "R2 connection successful."

echo "Uploading backup..."

rclone copy \
  --s3-no-check-bucket \
  "${ARCHIVE_FILE}" \
  "r2:${R2_BUCKET}/daily"

echo "Upload completed successfully."

echo "Cleaning up..."

rm -rf "${BACKUP_DIR}"
rm -f "${ARCHIVE_FILE}"

echo "====================================="
echo "Backup completed successfully."
echo "====================================="