#!/bin/bash

CONTAINER_NAME="aidocumines_db_prepare"
IMAGE_NAME="aidocumines-db_prepare:latest"
LOG_FILE="/app/logs/migrations_complete"

echo "Running migrations inside container: $CONTAINER_NAME"

# Check if the container exists
if ! docker ps -a --format "{{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
  echo "Container $CONTAINER_NAME does not exist. Creating it..."
  docker run -d --name $CONTAINER_NAME $IMAGE_NAME
fi

# Start the container if it is stopped
if ! docker ps --format "{{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
  echo "Starting container $CONTAINER_NAME..."
  docker start $CONTAINER_NAME
fi

# Skip health check and rely on manual validation
echo "Waiting for container $CONTAINER_NAME to be in 'running' state..."
while true; do
  STATUS=$(docker inspect -f '{{.State.Status}}' $CONTAINER_NAME || echo "exited")
  if [[ "$STATUS" == "running" ]]; then
    echo "$CONTAINER_NAME is running. Proceeding with migrations."
    break
  elif [[ "$STATUS" == "exited" ]]; then
    echo "$CONTAINER_NAME exited. Checking logs for errors..."
    docker logs $CONTAINER_NAME
    exit 1
  fi
  sleep 5
done

# Run makemigrations and migrate for all apps dynamically
echo "Creating and applying migrations for all apps..."
docker exec $CONTAINER_NAME bash -c "
  python manage.py makemigrations &&
  python manage.py migrate
"
if [[ $? -ne 0 ]]; then
  echo "Error during migrations. Exiting..."
  docker logs $CONTAINER_NAME
  exit 1
fi

# Log completion
if docker exec $CONTAINER_NAME test -f "$LOG_FILE"; then
  echo "Migrations already completed previously."
else
  echo "All migrations completed successfully!"
  docker exec $CONTAINER_NAME bash -c "touch $LOG_FILE"
fi

# Stop the container if necessary
if docker ps --format "{{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
  echo "Stopping container $CONTAINER_NAME..."
  docker stop $CONTAINER_NAME
fi
