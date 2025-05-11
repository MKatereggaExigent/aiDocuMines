#!/bin/bash

BASE_DIR="media/uploads"

echo "🔍 Safely scanning for truly empty subdirectories under $BASE_DIR ..."

# Only look inside subdirectories, not the BASE_DIR itself
find "$BASE_DIR" -mindepth 1 -type d | while read -r dir; do
    # Count number of regular files under the folder
    file_count=$(find "$dir" -type f | wc -l)

    if [ "$file_count" -eq 0 ]; then
        echo "🧹 Deleting: $dir"
        rm -rf "$dir"
    fi
done

echo "✅ Safe cleanup completed."

