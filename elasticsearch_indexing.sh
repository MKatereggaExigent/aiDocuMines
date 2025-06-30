#!/bin/bash

echo "⏳ Running Elasticsearch index initializations inside the Docker container..."

docker exec -i aidocumines_web bash << 'EOF'
python manage.py shell << 'PYTHON_EOF'
from core.elastic_indexes import (
    RunIndex,
    FileIndex,
    MetadataIndex,
    EndpointResponseTableIndex,
    WebhookIndex,
)

RunIndex.init()
FileIndex.init()
MetadataIndex.init()
EndpointResponseTableIndex.init()
WebhookIndex.init()

print("✅ Indices created successfully.")
PYTHON_EOF
EOF

