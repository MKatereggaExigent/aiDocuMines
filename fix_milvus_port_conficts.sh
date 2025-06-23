#!/usr/bin/env bash

# This is one example of the container you could remove and put back up
docker rm -f aidocumines_milvus_etcd

docker compose up -d --force-recreate milvus-etcd milvus-minio milvus-minio-init milvus

