#!/bin/bash
# Re-applies the CORS header fix to the Nginx proxy container
# Run this if the CapRover Swarm proxy container gets recreated
set -euo pipefail

CONTAINER=$(docker ps --filter name=srv-captain--aidocumines-api-layer --format "{{.ID}}" | head -1)

if [ -z "$CONTAINER" ]; then
  echo "ERROR: No aidocumines-api-layer proxy container found."
  exit 1
fi

echo "Fixing CORS headers in container: $CONTAINER"
docker exec "$CONTAINER" sed -i \
  's/x-client-id, x-client-secret/x-client-id, x-client-secret, x-role, x-user-id/' \
  /etc/nginx/conf.d/default.conf && \
docker exec "$CONTAINER" nginx -s reload && \
echo "CORS fix applied successfully."
