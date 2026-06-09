#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting incidentbot..."
exec python3 main.py
