#!/bin/bash
set -e

echo "============================================================"
echo "🚀 STARTING RAPIDREPORTZ BACKEND CONTAINER"
echo "============================================================"

# Check if we're in the right directory
echo "📁 Current directory: $(pwd)"
echo "📋 Files in current directory:"
ls -la

# Run database migrations if alembic exists
if [ -d "/app/alembic" ]; then
    echo "============================================================"
    echo "🔄 Running database migrations..."
    echo "============================================================"
    alembic upgrade head
    echo "✅ Migrations completed successfully"
else
    echo "============================================================"
    echo "⚠️  Alembic directory not found at /app/alembic"
    echo "📌 Database tables will be created by SQLAlchemy on startup"
    echo "============================================================"
fi

# Start the application
echo "============================================================"
echo "🌟 Starting FastAPI application with Uvicorn..."
echo "============================================================"

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ ERROR: main.py not found in $(pwd)"
    echo "📋 Files available:"
    ls -la
    exit 1
fi

echo "✅ main.py found, starting server..."
echo "📡 Host: 0.0.0.0"
echo "🔌 Port: ${PORT:-8080}"
echo "============================================================"

# Start uvicorn
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level info
