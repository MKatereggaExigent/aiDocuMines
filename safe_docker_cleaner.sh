#!/usr/bin/env bash

docker builder prune -a
docker image prune -a -f
docker container prune -f
docker volume prune -f

