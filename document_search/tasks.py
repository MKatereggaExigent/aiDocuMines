"""
document_search.tasks
~~~~~~~~~~~~~~~~~~~~

Celery tasks for background indexing & re-indexing.

Highlights
----------
• ONE Milvus collection → memory stays bounded.
• Partition-per-user (`user_<id>`) → zero data-leak risk.
• Idempotent indexing  → re-runs safe with force=True.
• Embeddings cached in VectorChunk → rebuild Milvus anytime.

Dependencies
------------
Celery worker already running in your project (e.g. `celery -A aiDocuMines worker -l info`).

Adjust MILVUS_* or PARTITION_PREFIX in `config.py` if needed.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Tuple

from celery import shared_task
from django.db import transaction
from django.core.cache import cache
from document_search.models import SearchQueryLog 

from core.models import File
from document_search.models import VectorChunk
from document_search.utils import compute_chunks

from document_search.utils import preview_for_file

# ───────────────────────────── Config & constants ───────────────────────────
try:
    from document_search import config
    MILVUS_HOST = getattr(config, "MILVUS_HOST", "localhost")
    MILVUS_PORT = getattr(config, "MILVUS_PORT", "19530")
    COLLECTION_NAME = getattr(config, "COLLECTION_NAME", "doc_embeddings")
    PARTITION_PREFIX = getattr(config, "PARTITION_PREFIX", "user_")
except ImportError:
    MILVUS_HOST = "localhost"
    MILVUS_PORT = "19530"
    COLLECTION_NAME = "doc_embeddings"
    PARTITION_PREFIX = "user_"

VECTOR_DIM = 384          # MiniLM / BGE-small default, stay in sync with utils.py
BATCH_SZ   = 100          # Milvus insert batch size

LOGGER = logging.getLogger(__name__)

# ───────────────────────────── Milvus bootstrap ─────────────────────────────
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)

def _ensure_collection() -> Collection:
    """Connect and create the single global collection if absent."""
    if not connections.has_connection("default"):
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)

    if not utility.has_collection(COLLECTION_NAME):
        LOGGER.info("Creating Milvus collection '%s' …", COLLECTION_NAME)

        # ── inside _ensure_collection() ──────────────────────────────────────────
        schema = CollectionSchema(
            [
                FieldSchema("pk",        DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema("file_id",   DataType.INT64),
                FieldSchema("chunk_hash", DataType.INT64),  # 👈 new field for dedup
                FieldSchema("source",    DataType.VARCHAR, max_length=100),     # filename
                FieldSchema("chunk_text", DataType.VARCHAR, max_length=2000),   # <- rename!
                FieldSchema("vector",    DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
            ],
            description="Chunked document embeddings (multi-tenant)",
        )

        coll = Collection(name=COLLECTION_NAME, schema=schema)
        coll.create_index(
            field_name="vector",
            index_params={
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128},
            },
        )
    return Collection(COLLECTION_NAME)


def _ensure_partition(coll: Collection, name: str) -> None:
    """Create partition for user if missing."""
    if not coll.has_partition(name):
        coll.create_partition(name)


def _insert_batches(
    coll: Collection,
    rows: List[Tuple[int, int, str, str, List[float]]],   # file_id, src, text, vec
    partition: str,
    batch: int = BATCH_SZ,
) -> None:
    """Safe batched insert to Milvus."""
    for i in range(0, len(rows), batch):
        slice_ = rows[i: i + batch]
        try:
            coll.insert(
                [
                    [r[0] for r in slice_],  # file_id
                    [r[1] for r in slice_],  # chunk_hash
                    [r[2] for r in slice_],  # source  (filename)
                    [r[3] for r in slice_],  # chunk_text
                    [r[4] for r in slice_],  # vector
                ],
                partition_name=partition,
            )
        except Exception as exc:
            LOGGER.error("Milvus insert error @batch %s: %s", i // batch, exc)


def _partition_name(user_id: int) -> str:
    return f"{PARTITION_PREFIX}{user_id}"


# ───────────────────────────── Celery tasks ─────────────────────────────────
@shared_task(name="document_search.index_file")
def index_file(file_id: int, force: bool = False) -> dict:
    """
    Index a single File into Milvus + VectorChunk.

    Parameters
    ----------
    file_id : PK of core.File
    force   : Re-index even if chunks already exist.
    """
    try:
        file = File.objects.select_related("user").get(pk=file_id)
    except File.DoesNotExist:
        LOGGER.error("File %s does not exist.", file_id)
        return {"status": "error", "detail": "file-not-found"}

    if not force and file.vector_chunks.exists():
        LOGGER.debug("File %s already indexed; skipping.", file_id)
        return {"status": "skipped"}

    # 1️⃣ Extract ▸ Chunk ▸ Embed
    chunks, vectors = compute_chunks(file.filepath)
    if not chunks:
        LOGGER.warning("No extractable text for %s.", file.filename)
        return {"status": "empty"}

    # 2️⃣ Persist to Django (atomic)
    with transaction.atomic():
        if force:
            file.vector_chunks.all().delete()
        VectorChunk.objects.bulk_create(
            [
                VectorChunk(
                    file=file,
                    user_id=file.user_id,
                    chunk_index=i,
                    chunk_text=txt,
                    embedding=vec,
                )
                for i, (txt, vec) in enumerate(zip(chunks, vectors))
            ],
            batch_size=500,
        )

    # 3️⃣ Insert into Milvus
    coll = _ensure_collection()
    part = _partition_name(file.user_id)
    _ensure_partition(coll, part)
    coll.load(partition_names=[part])          # memory-friendly

    # _insert_batches(
    #     coll,
    #     [
    #         (file.id, file.filename, txt, vec) for txt, vec in zip(chunks, vectors)
    #     ],
    #     partition=part,
    # )


    seen = set()
    rows = []
    for txt, vec in zip(chunks, vectors):
        h = hash(txt)
        if h in seen:
            continue
        seen.add(h)
        rows.append((file.id, h, file.filename, txt, vec))

    _insert_batches(coll, rows, partition=part)

    coll.flush()
    coll.release()

    LOGGER.info("✅ Indexed %s chunks for file %s → partition %s",
                len(chunks), file_id, part)
    return {"status": "ok", "chunks": len(chunks)}


@shared_task(name="document_search.bulk_reindex")
def bulk_reindex() -> dict:
    """
    Queue indexing for all Files missing VectorChunks.
    """
    unindexed: Iterable[File] = (
        File.objects.filter(vector_chunks__isnull=True)
        .order_by("id")
        .distinct()
    )
    count = 0
    for f in unindexed:
        index_file.delay(f.id)
        count += 1

    LOGGER.info("📥 Enqueued %s files for indexing.", count)
    return {"queued": count}



@shared_task(name="document_search.exec_search")
def exec_search(user_id: int, query: str, file_id: int | None, top_k: int) -> list[dict]:
    """
    Heavy-weight search:
        • embed query
        • Milvus ANN search (user partition)
        • return [{file_id, chunk_text, score}, …]
    """
    cache_key = f"search:{user_id}:{file_id}:{top_k}:{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached  # ⏩ hot path

    # ── embed ───────────────────────────────────────────────────────────
    from document_search.utils import embed_text
    q_vec = embed_text(query)

    # ── Milvus ──────────────────────────────────────────────────────────
    coll = _ensure_collection()
    part = _partition_name(user_id)

    _ensure_partition(coll, part)           # ✅ add this line
    coll.load(partition_names=[part])       # avoids load failure

    if isinstance(file_id, list):
        expr = f"file_id in {tuple(file_id)}"
    elif file_id:
        expr = f"file_id == {file_id}"
    else:
        expr = ""

    import time
    t0 = time.time()                                        # ⏱️ start

    res = coll.search(
        data=[q_vec],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        expr=expr,
        output_fields=["file_id", "chunk_text"],
    )
    duration = int((time.time() - t0) * 1000)               # ⏱️ ms
    coll.release()

    seen = set()
    hits = []
    for hit in res[0]:
        fid   = int(hit.entity.get("file_id"))
        ctext = hit.entity.get("chunk_text", "")
        preview = preview_for_file(fid)
        chash = hash(ctext)
        if chash in seen:
            continue
        seen.add(chash)

        snippet = (ctext[:297] + "…") if len(ctext) > 300 else ctext
        snippet = snippet.replace("\n", "  \n")  # Markdown line breaks

        hits.append({
            "file_id": fid,
            "snippet_md": snippet,
            "score": float(hit.score),
            "preview": preview,
        })
        if len(hits) >= top_k:
            break

   # hits = [
   #     {
   #         "file_id": int(hit.entity.get("file_id")),
   #         "chunk_text": hit.entity.get("chunk_text", ""),
   #         "score": float(hit.score),
   #     }
   #     for hit in res[0]
   # ]

    # ── cache & DB log ──────────────────────────────────────────────────
    cache.set(cache_key, hits, timeout=60 * 60 * 6)  # 6 h

    SearchQueryLog.objects.create(
        user_id=user_id,
        file_id=file_id if File.objects.filter(id=file_id).exists() else None,
        query_text=query,
        top_k=top_k,
        duration_ms=duration,
        result_count=len(hits),
        result_json=hits,
    )

    return hits



'''
@shared_task(name="document_search.exec_search")
def exec_search(user_id: int, query: str, file_id: int | None, top_k: int) -> list[dict]:
    """
    Heavy-weight search:
        • embed query
        • Milvus ANN search (user partition)
        • return [{file_id, chunk_text, score}, …]
    """

    cache_key = f"search:{user_id}:{file_id}:{top_k}:{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached                      # ⏩ hot path

    # ── embed ───────────────────────────────────────────────────────────
    from document_search.utils import _get_model, embed_text
    q_vec = embed_text(query)

    # ── Milvus ──────────────────────────────────────────────────────────
    coll = _ensure_collection()
    part = _partition_name(user_id)
    coll.load(partition_names=[part])

    expr = f"file_id == {file_id}" if file_id else ""
    res = coll.search(
        data=[q_vec],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        expr=expr,
        output_fields=["file_id", "chunk_text"],
    )
    coll.release()

    hits = [
        {
            "file_id": int(hit.entity.get("file_id")),
            "chunk_text": hit.entity.get("chunk_text", ""),
            "score": float(hit.score),
        }
        for hit in res[0]
    ]

    # ── cache & DB log ──────────────────────────────────────────────────
    cache.set(cache_key, hits, timeout=60 * 60 * 6)          # 6 h
    SearchQueryLog.objects.create(
        user_id=user_id,
        query=query,
        file_id=file_id,
        top_k=top_k,
        result_json=hits,
    )
    return hits
'''


# ───────────── Optional alias for semantic clarity ─────────────
process_file_for_search = index_file

