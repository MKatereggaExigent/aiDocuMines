#!/usr/bin/env bash
docker ps -a --filter "ancestor=caprover/caprover-placeholder-app:latest" --format "{{.ID}}" | xargs -r docker rm -f
