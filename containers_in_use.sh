#!/usr/bin/env bash
docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Names}}"
