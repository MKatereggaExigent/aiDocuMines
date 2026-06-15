#!/usr/bin/env bash

# Restart all critical app + DB containers
docker restart aidocumines_api_layer_db
docker restart aidocumines_redis
docker restart aidocumines_web
docker restart aidocumines_celery
docker restart aidocumines_celery_beat
docker restart aidocumines_file_monitor
docker restart aidocumines_milvus
docker restart aidocumines_elasticsearch
docker restart aidocumines_ollama

# Reapply CORS fix to the CapRover Swarm proxy container
# (handles OPTIONS preflight directly at nginx level, bypassing Django)
PROXY_CONTAINER=$(docker ps --filter name=srv-captain--aidocumines-api-layer --format "{{.ID}}" | head -1)
if [ -n "$PROXY_CONTAINER" ]; then
  docker exec "$PROXY_CONTAINER" sed -i \
    's/x-client-id, x-client-secret/x-client-id, x-client-secret, x-role, x-user-id/' \
    /etc/nginx/conf.d/default.conf 2>/dev/null
  docker exec "$PROXY_CONTAINER" nginx -s reload 2>/dev/null
  echo "CORS fix applied to proxy container: $PROXY_CONTAINER"
fi
