#!/usr/bin/env bash

set -e

echo "Run apply migrations..."
alembic revision --autogenerate -m "init tables"
alembic upgrade head
echo "Migrations applied"

exec "$@"
