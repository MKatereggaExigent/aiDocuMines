#!/bin/bash

echo "[+] Truncating all Docker logs..."
find /var/lib/docker/containers/ -name "*.log" -exec truncate -s 0 {} \;

echo "[+] Running system prune..."
docker system prune -af --volumes

echo "[+] Docker cleanup done."
df -h

