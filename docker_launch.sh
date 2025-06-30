#!/usr/bin/env bash

set -e  # Stop on any error

echo "🛑 Stopping any non-Docker processes using relevant ports..."
PORTS=(8020 6381 15672 8050)  # Exclude Docker-managed ports like 5432 (PostgreSQL) and 6379 (Redis)

for PORT in "${PORTS[@]}"; do
    PIDS=$(lsof -t -i:$PORT || true)
    if [[ ! -z "$PIDS" ]]; then
        echo "🔪 Killing processes on port $PORT: $PIDS..."
        for PID in $PIDS; do
            kill -9 "$PID" 2>/dev/null || echo "⚠️ Failed to kill PID $PID"
        done
    else
        echo "✅ No process running on port $PORT."
    fi
done  # 🔹 Closing loop properly


# 1️⃣ **Ensure Docker is Running**
if ! docker info >/dev/null 2>&1; then
    echo "❌ ERROR: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "🧹 Cleaning up Docker environment..."
docker-compose down -v || echo "⚠️ Warning: Failed to bring down containers."
docker system prune -af || echo "⚠️ Warning: Failed to prune unused images and containers."
docker volume prune -af || echo "⚠️ Warning: Failed to prune unused volumes."

echo "🚀 Starting Docker containers..."
docker-compose build || { echo "❌ ERROR: Build failed!"; exit 1; }
docker-compose up --build -d || { echo "❌ ERROR: Failed to start containers!"; exit 1; }

# 2️⃣ **Wait for PostgreSQL & Redis to be Healthy**
echo "⏳ Waiting for services to be healthy..."
TRIES=20
while [[ $TRIES -gt 0 ]]; do
    DB_STATUS=$(docker inspect --format='{{.State.Health.Status}}' aidocumines_db 2>/dev/null || echo "unhealthy")
    REDIS_STATUS=$(docker inspect --format='{{.State.Health.Status}}' aidocumines_redis 2>/dev/null || echo "unhealthy")

    if [[ "$DB_STATUS" == "healthy" && "$REDIS_STATUS" == "healthy" ]]; then
        echo "✅ Database and Redis are healthy!"
        break
    fi

    echo "⏳ Waiting... DB: $DB_STATUS, Redis: $REDIS_STATUS ($TRIES retries left)"
    ((TRIES--))
    sleep 3
done

if [[ "$DB_STATUS" != "healthy" || "$REDIS_STATUS" != "healthy" ]]; then
    echo "❌ ERROR: Database or Redis did not become healthy in time!"
    docker logs aidocumines_db || echo "⚠️ Could not retrieve DB logs."
    docker logs aidocumines_redis || echo "⚠️ Could not retrieve Redis logs."
    exit 1
fi

echo "✅ All services started successfully!"
