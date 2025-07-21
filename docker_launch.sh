#!/usr/bin/env bash

set -e  # Stop on any error

# 1️⃣ Ensure Docker is Running
if ! docker info >/dev/null 2>&1; then
    echo "❌ ERROR: Docker is not running. Please start Docker and try again."
    exit 1
fi

# ⭐️ NEW (ROBUST): Let Docker Compose handle the .env file ⭐️
# Docker Compose natively reads the .env file in the project directory.
# No manual export is needed.
if [ ! -f .env ]; then
    echo "⚠️ Warning: .env file not found. Docker Compose may fail to substitute variables."
fi

echo "🧹 Cleaning up Docker environment..."
docker-compose down -v --remove-orphans || echo "⚠️ Warning: Failed to bring down containers."

echo "🚀 Starting Docker containers..."
# The --build flag is included with 'up', so 'docker-compose build' separately is redundant.
docker-compose up --build -d || { echo "❌ ERROR: Failed to start containers!"; exit 1; }

# --- DEBUGGING STEP: Check environment inside the running container ---
echo
echo "🔍 DEBUG: Checking environment variables INSIDE the running 'db' container..."
sleep 5 # Wait a few seconds for the container to initialize
docker exec aidocumines_api_layer_db env | grep POSTGRES || echo "⚠️ Could not inspect environment of db container."
echo "----------------------------------------------------"
echo

# 2️⃣ Wait for PostgreSQL & Redis to be Healthy
echo "⏳ Waiting for services to be healthy..."
TRIES=20
while [[ $TRIES -gt 0 ]]; do
    DB_STATUS=$(docker inspect --format='{{.State.Health.Status}}' aidocumines_api_layer_db 2>/dev/null || echo "unhealthy")
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
    echo "--- LOGS FOR aidocumines_api_layer_db ---"
    docker logs aidocumines_api_layer_db
    exit 1
fi


echo "⏳ Waiting for Ollama to be ready..."
TRIES=20
while [[ $TRIES -gt 0 ]]; do
    STATUS=$(curl -s http://localhost:11434/api/tags || echo "fail")
    if [[ "$STATUS" != "fail" ]]; then
        echo "✅ Ollama is ready!"
        break
    fi
    echo "⏳ Waiting on Ollama... ($TRIES retries left)"
    ((TRIES--))
    sleep 3
done

if [[ "$STATUS" == "fail" ]]; then
    echo "❌ ERROR: Ollama failed to become available!"
    docker logs aidocumines_ollama
    exit 1
fi


echo "✅ All services started successfully!"
