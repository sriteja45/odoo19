#!/bin/bash

set -e

RESTORE_DIR="/tmp/restore"

mkdir -p "${RESTORE_DIR}"

echo "====================================="
echo "Starting Odoo Restore"
echo "====================================="

export PGPASSWORD="${DB_PASSWORD}"

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

echo "Finding latest backup..."

LATEST_FILE=$(rclone lsf \
  "r2:${R2_BUCKET}/daily" \
  --files-only \
  | sort \
  | tail -n 1)

if [ -z "${LATEST_FILE}" ]; then
    echo "No backup files found"
    exit 1
fi

echo "Latest Backup: ${LATEST_FILE}"

echo "Downloading backup..."

rclone copy \
  --s3-no-check-bucket \
  "r2:${R2_BUCKET}/daily/${LATEST_FILE}" \
  "${RESTORE_DIR}"

ZIP_FILE="${RESTORE_DIR}/${LATEST_FILE}"

echo "Extracting backup..."

unzip -o "${ZIP_FILE}" -d "${RESTORE_DIR}"

echo "====================================="
echo "Extracted Filestore Statistics"
echo "====================================="

find "${RESTORE_DIR}/filestore" -type f | wc -l
du -sh "${RESTORE_DIR}/filestore"

echo "Detecting original database..."

SOURCE_FILESTORE=$(find "${RESTORE_DIR}/filestore" \
  -mindepth 1 \
  -maxdepth 1 \
  -type d | head -n 1)

ORIGINAL_DB_NAME=$(basename "${SOURCE_FILESTORE}")

echo "Finding next restore database number..."

NEXT_NUM=$(psql \
  -h "${DB_HOST}" \
  -U "${DB_USER}" \
  -d postgres \
  -tAc "
SELECT COALESCE(
  MAX(
    CASE
      WHEN datname ~ '^restore[0-9]+_${ORIGINAL_DB_NAME}$'
      THEN substring(datname from 'restore([0-9]+)_')::int
      ELSE 0
    END
  ),0
)+1
FROM pg_database;
")

RESTORE_DB_NAME="restore${NEXT_NUM}_${ORIGINAL_DB_NAME}"

echo "Original DB : ${ORIGINAL_DB_NAME}"
echo "Restore DB  : ${RESTORE_DB_NAME}"

echo "Creating restore database..."

createdb \
  -h "${DB_HOST}" \
  -U "${DB_USER}" \
  "${RESTORE_DB_NAME}"

echo "Restoring PostgreSQL database..."

pg_restore \
  --verbose \
  --no-owner \
  --no-privileges \
  -h "${DB_HOST}" \
  -U "${DB_USER}" \
  -d "${RESTORE_DB_NAME}" \
  "${RESTORE_DIR}/database.dump"

echo "====================================="
echo "Source Filestore Statistics"
echo "====================================="

find "${SOURCE_FILESTORE}" -type f | wc -l
du -sh "${SOURCE_FILESTORE}"

echo "Restoring filestore..."

rm -rf "/var/lib/odoo/filestore/${RESTORE_DB_NAME}"

cp -r \
  "${SOURCE_FILESTORE}" \
  "/var/lib/odoo/filestore/${RESTORE_DB_NAME}"

echo "====================================="
echo "Restored Filestore Statistics"
echo "====================================="

find "/var/lib/odoo/filestore/${RESTORE_DB_NAME}" -type f | wc -l
du -sh "/var/lib/odoo/filestore/${RESTORE_DB_NAME}"

echo "Filestore restored successfully."

echo "====================================="
echo "Restore completed successfully"
echo "Database : ${RESTORE_DB_NAME}"
echo "Restore files kept in: ${RESTORE_DIR}"
echo "====================================="

# DEBUG MODE
# Cleanup disabled intentionally
# rm -rf "${RESTORE_DIR}"