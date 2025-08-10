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
from pymilvus import Collection
from document_search.utils import _get_model

from django.db.models import Q
from datetime import datetime
from document_operations.models import FileAccessEntry

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

    # NEW: concatenate all text to classify the entire file
    all_text = " ".join(chunks) if chunks else ""
    if all_text.strip():
        embed_model = _get_model()
        doc_embedding = embed_model.encode([all_text])[0]

        # Simple label prototypes for semantic similarity
        labels = {
                    "Contract": "This document is a legal contract between parties.",
                    "Legal Agreement": "This document outlines legal obligations, rights, or terms between parties.",
                    "Non-Disclosure Agreement": "This document restricts sharing confidential information.",
                    "Service Level Agreement": "This document specifies performance standards and responsibilities between service providers and clients.",
                    "Legal Complaint": "This document is a legal complaint filed in court.",
                    "Court Order": "This document contains orders or judgments issued by a court.",
                    "Will": "This document details the distribution of a person's estate after death.",
                    "Policy Document": "This document describes official rules or guidelines.",
                    "License": "This document grants legal permission for an activity or use.",
                    "Patent": "This document protects intellectual property rights.",
                    "Financial Report": "This document describes financial results, performance, or analysis.",
                    "Balance Sheet": "This document summarizes assets, liabilities, and equity of an entity.",
                    "Income Statement": "This document details revenue and expenses over a period.",
                    "Invoice": "This document is an invoice for payment.",
                    "Receipt": "This document acknowledges payment received.",
                    "Tax Form": "This document relates to tax filing or reporting obligations.",
                    "Bank Statement": "This document shows transactions in a bank account.",
                    "Audit Report": "This document provides an independent financial audit opinion.",
                    "Budget": "This document plans income and expenses for a period.",
                    "Payroll Report": "This document summarizes employee wages and deductions.",
                    "Medical Report": "This document contains medical or health records.",
                    "Medical Prescription": "This document is a prescription for medication or treatment.",
                    "Lab Result": "This document shows medical or laboratory test outcomes.",
                    "Patient Summary": "This document summarizes patient medical history and conditions.",
                    "Insurance Claim": "This document is submitted to request insurance reimbursement.",
                    "Business Proposal": "This document proposes business plans, services, or products.",
                    "Business Plan": "This document outlines business strategies, objectives, and forecasts.",
                    "Meeting Minutes": "This document records discussion points and decisions from meetings.",
                    "Memo": "This document is a formal written message for internal communication.",
                    "Resume": "This document summarizes an individual's work experience and skills.",
                    "Cover Letter": "This document accompanies a resume to express interest in a job.",
                    "Letter": "This document is a formal or informal letter.",
                    "Email": "This document is an electronic mail communication.",
                    "Press Release": "This document announces news or events to the media.",
                    "Brochure": "This document is a marketing or informational pamphlet.",
                    "Advertisement": "This document promotes products, services, or events.",
                    "User Manual": "This document provides instructions for using a product or system.",
                    "Technical Specification": "This document describes detailed technical requirements and designs.",
                    "Log File": "This document contains logs from systems, servers, or applications.",
                    "Standard Operating Procedure": "This document describes step-by-step instructions for business processes.",
                    "Research Paper": "This document presents academic research findings.",
                    "Thesis": "This document is a lengthy academic dissertation.",
                    "Lecture Notes": "This document contains notes from educational lectures.",
                    "Patent Application": "This document is filed to seek intellectual property protection.",
                    "Permit": "This document grants legal permission for specific activities.",
                    "Certificate": "This document verifies a fact or achievement.",
                    "Notice": "This document communicates official information or updates.",
                    "Form": "This document contains fields for data collection or submission.",
                    "Checklist": "This document lists tasks or items to complete or verify.",
                    "Schedule": "This document details timelines or time-based plans.",
                    "Statement of Work": "This document defines project deliverables and responsibilities.",
                    "Bill of Lading": "This document acknowledges receipt of goods for shipment.",
                    "Purchase Order": "This document authorizes the purchase of goods or services.",
                    "Agenda": "This document lists topics to be discussed in a meeting.",
                    "Transcript": "This document records spoken words or conversations.",
                    "Policy Brief": "This document provides summaries of policy issues and recommendations.",
                    "Guideline": "This document offers recommendations for best practices.",
                    "FAQ": "This document lists frequently asked questions and answers.",
                    "Summary": "This document provides a condensed version of longer content.",
                    "Newsletter": "This document provides regular updates or news to a group of readers.",
                    "White Paper": "This document provides authoritative information or solutions on a topic.",
                    "Case Study": "This document analyzes a specific example or scenario in detail.",
                    "Project Report": "This document summarizes progress, findings, or results of a project.",
                    "Privacy Policy": "This document explains how personal data is collected and used.",
                    "Terms and Conditions": "This document defines rules and legal agreements for using products or services.",
                    "Unclassified": "This document does not fit into any known category or cannot be determined."
                }
        label_texts = list(labels.values())
        label_names = list(labels.keys())
        label_embeddings = embed_model.encode(label_texts)

        from sklearn.metrics.pairwise import cosine_similarity
        scores = cosine_similarity([doc_embedding], label_embeddings)
        best_idx = scores.argmax()
        best_label = label_names[best_idx]

        file.document_type = best_label
        file.save(update_fields=["document_type"])

        LOGGER.info(f"→ File {file_id} classified as: {best_label}")
    else:
        file.document_type = "Unknown"
        file.save(update_fields=["document_type"])
        LOGGER.info(f"→ File {file_id} classified as: Unknown")

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
    coll.load(partition_names=[part])


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


@shared_task(name="document_search.semantic_search_task")
def semantic_search_task(user_id: int, query: str, top_k: int, file_id: int | None, filters: dict) -> list[dict]:
    """
    Perform semantic search asynchronously.
    """
    try:
        # Embed query
        embed_model = _get_model()
        query_vector = embed_model.encode([query])[0]

        # ✅ FIX: connect and ensure collection
        collection = _ensure_collection()
        collection.load()

        # Optionally load only user's partition
        partition = _partition_name(user_id)
        _ensure_partition(collection, partition)
        collection.load(partition_names=[partition])

        # Build filter expression
        if isinstance(file_id, list):
            expr = f"file_id in {tuple(file_id)}"
        elif file_id:
            expr = f"file_id == {file_id}"
        else:
            expr = ""

        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            expr=expr,
            output_fields=["file_id", "chunk_text"],
        )

        file_ids = list({hit.entity.get("file_id") for hit in results[0]})

        # Build Postgres filters
        # q = Q(user_id=user_id)

        # Get files owned by the user or shared with them

        # 🔐 Get accessible file IDs (owned or shared)
        accessible_file_ids = list(
            File.objects.filter(uploaded_by_id=user_id).values_list("id", flat=True)
        ) + list(
            FileAccessEntry.objects.filter(user_id=user_id, can_read=True).values_list("file_id", flat=True)
        )

        q = Q(id__in=accessible_file_ids)  # ✅ Base filter

        # Optional: narrow to specific file_id(s)
        if file_ids:
            q &= Q(id__in=file_ids)  # intersection

        # Apply additional filters
        if filters.get("created_from"):
            q &= Q(created_at__gte=datetime.fromisoformat(filters["created_from"]))
        if filters.get("created_to"):
            q &= Q(created_at__lte=datetime.fromisoformat(filters["created_to"]))
        if filters.get("author"):
            q &= Q(metadata__author__icontains=filters["author"])
        if filters.get("project_id"):
            q &= Q(project_id=filters["project_id"])
        if filters.get("service_id"):
            q &= Q(service_id=filters["service_id"])

        '''
        accessible_file_ids = list(
            File.objects.filter(uploaded_by_id=user_id).values_list("id", flat=True)
        ) + list(
            FileAccessEntry.objects.filter(user_id=user_id, can_read=True).values_list("file_id", flat=True)
        )

        if filters.get("created_from"):
            q &= Q(created_at__gte=datetime.fromisoformat(filters["created_from"]))
        if filters.get("created_to"):
            q &= Q(created_at__lte=datetime.fromisoformat(filters["created_to"]))
        if filters.get("author"):
            q &= Q(metadata__author__icontains=filters["author"])
        if filters.get("project_id"):
            q &= Q(project_id=filters["project_id"])
        if filters.get("service_id"):
            q &= Q(service_id=filters["service_id"])
        if file_ids:
            q &= Q(id__in=file_ids)
            q = Q(id__in=accessible_file_ids)
        '''

        files = File.objects.filter(q).prefetch_related("metadata")

        results_out = []
        for file in files:
            metadata = file.metadata.first()
            results_out.append({
                "file_id": file.id,
                "filename": file.filename,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "document_type": file.document_type,
                "created_at": file.created_at,
                "author": metadata.author if metadata else None,
                "keywords": metadata.keywords if metadata else None,
                "chunk_text": next(
                    (hit.entity.get("chunk_text") for hit in results[0] if hit.entity.get("file_id") == file.id),
                    ""
                ),
                "score": next(
                    (hit.score for hit in results[0] if hit.entity.get("file_id") == file.id),
                    None
                )
            })

        return results_out

    except Exception as e:
        LOGGER.error(f"Error in semantic search task: {str(e)}")
        return {"error": str(e)}



# ───────────── Optional alias for semantic clarity ─────────────
process_file_for_search = index_file

