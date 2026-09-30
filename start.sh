#!/bin/sh
# Production entrypoint: create/upgrade schema once, then serve with gunicorn.
# A freshly-created database (e.g. Render's free Postgres, right after a first Blueprint
# deploy) can take a little longer to actually accept connections than the web service
# takes to start. Retry init-db a few times with a short wait instead of exiting on the
# first attempt - without this, one slow database start silently crashes the whole
# container (nothing ever binds to $PORT), which the platform then reports as a 502.
set -e
n=0
until python manage.py init-db; do
  n=$((n + 1))
  if [ "$n" -ge 10 ]; then
    echo "init-db still failing after 10 attempts - giving up. Check DATABASE_URL and that the database is reachable." >&2
    exit 1
  fi
  echo "init-db failed (attempt $n/10) - database may still be starting up, retrying in 3s..." >&2
  sleep 3
done
exec gunicorn wsgi:app --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --threads 2 --timeout 120 \
  --access-logfile - --error-logfile - --forwarded-allow-ips="*"
