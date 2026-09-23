#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# 1. Load environment variables from .env if it exists
if [ -f .env ]; then
	echo "Loading environment variables from .env..."
	set -o allexport
	source .env
	set +o allexport
fi

# Fallback DATABASE_URL if not provided via environment or .env
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://postgres:postgres@localhost:5432/salon_autozone}"

# 2. Run database migrations only if Alembic is configured
if [ -f alembic.ini ] && command -v alembic >/dev/null 2>&1; then
	echo "Running database migrations..."
	alembic upgrade head
else
	echo "Skipping migrations: Alembic config or command not found."
fi

# 3. Start Uvicorn app
echo "Starting application..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
