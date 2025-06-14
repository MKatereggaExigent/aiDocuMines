#!/usr/bin/env bash

echo "Restarting aiDocuMines CapRover containers..."

containers=$(docker ps --format '{{.Names}}' | grep '^srv-captain--aidocumines')

if [ -z "$containers" ]; then
  echo "❌ No matching containers found for 'aidocumines'"
  exit 1
fi

for name in $containers; do
  echo "🔄 Restarting $name ..."
  docker container restart "$name"
done

echo "✅ Restart complete."

