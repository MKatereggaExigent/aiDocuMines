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
