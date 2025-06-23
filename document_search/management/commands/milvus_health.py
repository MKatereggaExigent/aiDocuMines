"""
Health-check Milvus from inside Django.

Usage
-----

# from host (after `docker compose up`)
docker compose exec web python manage.py milvus_health

# or inside your running Django container
python manage.py milvus_health
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from datetime import datetime
from typing import List

from django.conf import settings
from django.core.management.base import BaseCommand

from pymilvus import (
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    connections,
    utility,
)
from sentence_transformers import SentenceTransformer

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ──────────────────────────────────────────────────────────────
# Config – falls back to env vars if not in settings.py
# ──────────────────────────────────────────────────────────────
MILVUS_HOST = getattr(settings, "MILVUS_HOST", os.getenv("MILVUS_HOST", "milvus"))
MILVUS_PORT = getattr(settings, "MILVUS_PORT", os.getenv("MILVUS_PORT", "19530"))
MODEL_NAME = "all-MiniLM-L6-v2"
COLL_NAME = "milvus_healthcheck"          # dropped at the end
VECTOR_DIM = 384
SAMPLE_TEXTS = [
    "Milvus is a cloud-native vector database.",
    "This is only a test vector.",
    "Document search feature health-check.",
    "High-throughput similarity search demo.",
    "End-to-end embedding & query cycle.",
]


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def connect() -> None:
    """Connect (or reuse) the default Milvus alias."""
    if not connections.has_connection("default"):
        LOGGER.info("🔗  Connecting to Milvus at %s:%s …", MILVUS_HOST, MILVUS_PORT)
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    LOGGER.info("✅  Connection established")


def prepare_collection() -> Collection:
    """Create a temporary collection for the health-check."""
    if utility.has_collection(COLL_NAME):
        LOGGER.warning("⚠️  Old '%s' collection found – dropping first", COLL_NAME)
        Collection(COLL_NAME).drop()

    schema = CollectionSchema(
        fields=[
            FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema("content", DataType.VARCHAR, max_length=1000),
            FieldSchema("vector", DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
        ],
        description="Temporary health-check collection",
    )

    coll = Collection(name=COLL_NAME, schema=schema)
    LOGGER.info("✅  Collection '%s' created", COLL_NAME)
    return coll


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = SentenceTransformer(MODEL_NAME)
    LOGGER.info("🤖  Encoding %d sample sentences with %s …", len(texts), MODEL_NAME)
    return model.encode(texts).tolist()


def run_roundtrip() -> None:
    """Full cycle: connect → create → insert → search → drop."""
    connect()
    coll = prepare_collection()

    vectors = embed_texts(SAMPLE_TEXTS)
    coll.insert([SAMPLE_TEXTS, vectors])
    coll.flush()

    # Create vector index for faster search
    coll.create_index(
        field_name="vector",
        index_params={
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 64},
        },
    )
    coll.load()

    # Search using first text as query
    query_vec = [vectors[0]]
    results = coll.search(
        data=query_vec,
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=3,
        output_fields=["content"],
    )

    LOGGER.info("🔍  Top-3 search results:")
    for hit in results[0]:
        LOGGER.info("   • score %.4f  →  \"%s…\"", hit.score, hit.entity.get("content")[:60])

    coll.drop()
    LOGGER.info("🗑️  Temporary collection dropped – health-check successful")


# ──────────────────────────────────────────────────────────────
# Django Management Command
# ──────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = "Run Milvus connectivity + CRUD round-trip test"

    def handle(self, *args, **options):  # noqa: D401
        ts = datetime.utcnow().isoformat(timespec="seconds")
        LOGGER.info("🚑  Milvus health-check started @ %s UTC", ts)
        try:
            run_roundtrip()
            LOGGER.info("🎉  Milvus is UP and fully operational.")
            self.stdout.write(self.style.SUCCESS("Milvus health-check: PASSED"))
            sys.exit(0)
        except Exception as exc:
            LOGGER.error("❌  Milvus health-check FAILED\n%s", traceback.format_exc())
            self.stderr.write(self.style.ERROR(f"Milvus health-check failed: {exc}"))
            sys.exit(1)

