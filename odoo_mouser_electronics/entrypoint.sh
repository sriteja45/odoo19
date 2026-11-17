#!/bin/bash
set -e

echo "Generating Odoo config..."

envsubst < /etc/odoo/odoo.conf.template > /etc/odoo/odoo.conf
chmod 640 /etc/odoo/odoo.conf

echo "Waiting for PostgreSQL..."

until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER"; do
  sleep 2
done

echo "PostgreSQL is ready"

echo "Initializing Odoo modules..."

odoo -c /etc/odoo/odoo.conf -d "$DB_NAME" \
  -i base,Xevoria_electronics,language_and_currency,mouser_country_tax,admin_login_page,xevoria_redis_cache,xevoria_ai_chatbot, \
  --stop-after-init || true

echo "Updating Odoo modules..."

odoo -c /etc/odoo/odoo.conf -d "$DB_NAME" \
  -u all \
  --stop-after-init

echo "Starting Odoo..."

exec odoo -c /etc/odoo/odoo.conf -d "$DB_NAME" --dev=all
