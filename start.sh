#!/usr/bin/env bash
set -e

echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo "=== Seeding ticket categories ==="
python manage.py seed_categories

# Optional: create a superuser if it doesn't exist (requires env vars)
if [ -n "$SUPERUSER_EMAIL" ] && [ -n "$SUPERUSER_PASSWORD" ]; then
  echo "=== Ensuring superuser exists ==="
  python manage.py ensure_superuser
fi

echo "=== Starting Gunicorn ==="
exec gunicorn config.wsgi:application --log-file -