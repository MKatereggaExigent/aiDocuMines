#!/bin/bash

echo "==============================="
echo "Stopping all running containers"
echo "==============================="
docker ps -q | xargs -r docker stop

echo "==============================="
echo "Removing all containers"
echo "==============================="
docker ps -aq | xargs -r docker rm -f

echo "==============================="
echo "Removing all volumes"
echo "==============================="
docker volume ls -q | xargs -r docker volume rm

echo "==============================="
echo "Removing unused networks (optional)"
echo "==============================="
docker network prune -f

echo "==============================="
echo "System cleanup (optional)"
echo "==============================="
docker system prune -af --volumes

echo "Done."

