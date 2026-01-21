#!/bin/bash
set -e

echo "================================================"
echo "🚀 RapidReportz Backend Startup"
echo "================================================"
echo ""

# Run migrations (skip if fails - we use SQLAlchemy create_all)
echo "Checking database migrations..."
if alembic upgrade head 2>/dev/null; then
    echo "✅ Migrations applied successfully"
else
    echo "ℹ️  Migrations skipped (Using SQLAlchemy instead)"
fi

echo ""
echo "================================================"
echo "🎯 Starting Application Server"
echo "================================================"
echo ""

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
