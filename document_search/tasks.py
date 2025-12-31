"""
document_search.tasks
~~~~~~~~~~~~~~~~~~~

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
import time
from typing import Iterable, List, Tuple

from celery import shared_task
from django.db import transaction
from django.core.cache import cache
from django.db.models import Q
from django.contrib.auth import get_user_model
from datetime import datetime

from core.models import File, Run
from document_search.models import VectorChunk, SearchQueryLog
from document_search.utils import (
    compute_chunks,
    preview_for_file,
    _get_model,
    embed_text,   # used in exec_search
)

# Use the same access helper the views rely on
from document_operations.utils import get_user_accessible_file_ids

# Import report generation utility
from core.utils import generate_and_register_service_report

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

        schema = CollectionSchema(
            [
                FieldSchema("pk",         DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema("file_id",    DataType.INT64),
                FieldSchema("chunk_hash", DataType.INT64),                    # for dedup
                FieldSchema("source",     DataType.VARCHAR, max_length=100),  # filename
                FieldSchema("chunk_text", DataType.VARCHAR, max_length=2000),
                FieldSchema("vector",     DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
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
    rows: List[Tuple[int, int, str, str, List[float]]],   # (file_id, chunk_hash, source, chunk_text, vector)
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
                    [r[2] for r in slice_],  # source (filename)
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

    # ── Lightweight whole-doc type classification (single embed) ─────────
    all_text = " ".join(chunks) if chunks else ""
    if all_text.strip():
        embed_model = _get_model()
        doc_embedding = embed_model.encode([all_text])[0]

        # Expanded label set (grouped; keep strings concise)
        labels = {
            # Legal & Compliance
            "Contract": "Legal contract between parties with terms and signatures.",
            "Legal Agreement": "Legal obligations, rights, or terms between parties.",
            "NDA": "Non-disclosure agreement restricting sharing confidential information.",
            "SLA": "Service level agreement with performance standards and responsibilities.",
            "Court Order": "Orders or judgments issued by a court.",
            "Legal Complaint": "Formal legal complaint filed in court.",
            "Terms and Conditions": "Rules and legal agreements for using products or services.",
            "Privacy Policy": "Explains how personal data is collected and used.",
            "Policy Document": "Official rules or guidelines that must be followed.",
            "Permit": "Legal permission granted for specific activities.",
            "License": "Authorization document granting legal permission.",
            "Certificate": "Official document verifying a fact or achievement.",
            "Will": "Estate distribution instructions after death.",
            # Finance & Accounting
            "Financial Report": "Financial results, performance, or analysis.",
            "Income Statement": "Revenue and expenses over a period.",
            "Balance Sheet": "Assets, liabilities, and equity snapshot.",
            "Cash Flow Statement": "Cash inflows and outflows over a period.",
            "Budget": "Planned income and expenses for a period.",
            "Invoice": "Bill for payment with items and totals.",
            "Receipt": "Acknowledgment of payment received.",
            "Bank Statement": "Account transactions and balances.",
            "Audit Report": "Independent financial audit opinion.",
            "Payroll Report": "Employee wages and deductions summary.",
            "Purchase Order": "Authorization to buy goods or services.",
            "Bill of Lading": "Receipt of goods for shipment.",
            "Statement of Work": "Project deliverables, scope, and responsibilities.",
            # Business & Operations
            "Business Proposal": "Proposes plans, services, or products to a client.",
            "Business Plan": "Business strategies, objectives, and forecasts.",
            "RFP Response": "Response to a request for proposal.",
            "SOP": "Standard operating procedure with step-by-step instructions.",
            "Project Report": "Project progress, findings, or results.",
            "Meeting Minutes": "Discussion points and decisions from meetings.",
            "Memo": "Formal internal communication message.",
            "Agenda": "List of topics to be discussed in a meeting.",
            "Checklist": "Tasks or items to complete or verify.",
            "Schedule": "Timeline or plan with dates and times.",
            "Log File": "System, server, or application log entries.",
            "User Manual": "Instructions for using a product or system.",
            "Technical Specification": "Detailed technical requirements and designs.",
            "Runbook": "Operational procedures for incidents or maintenance.",
            "Architecture Diagram": "System architecture documentation overview.",
            # Sales & Marketing
            "Press Release": "Public announcement of news or events.",
            "Brochure": "Marketing or informational pamphlet.",
            "Advertisement": "Promotes products, services, or events.",
            "Price List": "Catalog of products or services with prices.",
            "Statement of Capabilities": "Company capabilities and differentiators.",
            # HR & Talent
            "Resume": "Work experience and skills summary.",
            "Cover Letter": "Letter expressing job interest accompanying a resume.",
            "Offer Letter": "Employment offer details and terms.",
            "Job Description": "Role responsibilities and required qualifications.",
            "Performance Review": "Employee performance evaluation.",
            # Medical & Insurance
            "Medical Report": "Medical or health record details and assessments.",
            "Prescription": "Medication or treatment directive by a clinician.",
            "Lab Result": "Medical or laboratory test outcomes.",
            "Patient Summary": "Patient medical history and conditions.",
            "Insurance Claim": "Request to insurer for reimbursement.",
            "EOB": "Explanation of benefits document from insurer.",
            # Research & Education
            "Research Paper": "Academic research findings and analysis.",
            "White Paper": "Authoritative information or solution on a topic.",
            "Case Study": "Detailed analysis of a specific example.",
            "Thesis": "Lengthy academic dissertation.",
            "Lecture Notes": "Notes from educational lectures.",
            "Transcript": "Verbatim record of spoken words or courses.",
            "Dataset Description": "Metadata and description for datasets.",
            # IT & Security
            "Security Policy": "Information security rules and standards.",
            "Vulnerability Report": "Security weaknesses and remediation.",
            "Penetration Test Report": "Results of simulated attacks and fixes.",
            "Incident Report": "Security incident details and timeline.",
            "Change Request": "Proposed system change and approvals.",
            "Release Notes": "Software release changes and fixes.",
            # Government & Public
            "Notice": "Official information or updates to the public.",
            "Regulatory Filing": "Submission to a regulator or exchange.",
            # Misc
            "FAQ": "Frequently asked questions and answers.",
            "Summary": "Condensed version of longer content.",
            "Newsletter": "Periodic news or updates for readers.",
            "Unclassified": "Document type cannot be determined.",
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
        LOGGER.info("→ File %s classified as: %s", file_id, best_label)
    else:
        file.document_type = "Unknown"
        file.save(update_fields=["document_type"])
        LOGGER.info("→ File %s classified as: Unknown", file_id)

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

    # 3️⃣ Insert into Milvus (partitioned by user)
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

    LOGGER.info("✅ Indexed %s chunks for file %s → partition %s", len(chunks), file_id, part)
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

'''
@shared_task(name="document_search.exec_search")
def exec_search(user_id: int, query: str, file_id: int | None, top_k: int) -> list[dict]:
    """
    Heavy-weight search:
        • embed query
        • Milvus ANN search (user partition)
        • return [{file_id, chunk_text, score, preview}, …]
    """
    cache_key = f"search:{user_id}:{file_id}:{top_k}:{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached  # ⏩ hot path

    # ── embed ───────────────────────────────────────────────────────────
    q_vec = embed_text(query)

    # ── Milvus ──────────────────────────────────────────────────────────
    coll = _ensure_collection()
    part = _partition_name(user_id)
    _ensure_partition(coll, part)
    coll.load(partition_names=[part])

    if isinstance(file_id, list):
        expr = f"file_id in {tuple(file_id)}"
    elif file_id:
        expr = f"file_id == {file_id}"
    else:
        expr = ""

    import time
    t0 = time.time()

    res = coll.search(
        data=[q_vec],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        expr=expr,
        output_fields=["file_id", "chunk_text"],
    )
    duration = int((time.time() - t0) * 1000)
    coll.release()

    seen_chunks = set()
    hits = []
    for hit in res[0]:
        fid   = int(hit.entity.get("file_id"))
        ctext = hit.entity.get("chunk_text", "")
        preview = preview_for_file(fid)
        chash = hash(ctext)
        if chash in seen_chunks:
            continue
        seen_chunks.add(chash)

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
'''

@shared_task(name="document_search.exec_search")
def exec_search(user_id: int, query: str, file_id: int | None, top_k: int) -> list[dict]:
    cache_key = f"search:v2:{user_id}:{file_id}:{top_k}:{hash(query)}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 1) Resolve access
    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return []

    from django.db.models import F
    accessible_ids = set(get_user_accessible_file_ids(user))

    # If caller passed file_id, tighten scope
    if file_id:
        accessible_ids &= {int(file_id)}
    if not accessible_ids:
        return []

    # 2) Determine which partitions to load (owners of accessible files)
    owner_rows = (
        File.objects
        .filter(id__in=accessible_ids)
        .values("id", "user_id")  # or "user_id" if that's your canonical owner field
    )
    owner_partitions = {f"user_{row['user_id']}" for row in owner_rows}

    # 3) Embed query
    q_vec = embed_text(query)

    # 4) Milvus search over only needed partitions + file_id expr
    coll = _ensure_collection()
    for p in owner_partitions:
        _ensure_partition(coll, p)
    coll.load(partition_names=list(owner_partitions))

    id_list = ",".join(map(str, sorted(accessible_ids)))
    expr = f"file_id in [{id_list}]"

    res = coll.search(
        data=[q_vec],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        expr=expr,
        output_fields=["file_id", "chunk_text"],
    )
    coll.release()

    # 5) Dedup + shape
    seen = set()
    hits = []
    for hit in res[0]:
        fid = int(hit.entity.get("file_id"))
        ctext = hit.entity.get("chunk_text", "")
        ch = hash(ctext)
        if ch in seen:
            continue
        seen.add(ch)

        snippet = (ctext[:297] + "…") if len(ctext) > 300 else ctext
        snippet = snippet.replace("\n", "  \n")

        hits.append({
            "file_id": fid,
            "snippet_md": snippet,
            "score": float(hit.score),
            "preview": preview_for_file(fid),
        })
        if len(hits) >= top_k:
            break

    cache.set(cache_key, hits, timeout=60 * 60 * 6)
    SearchQueryLog.objects.create(
        user_id=user_id,
        file_id=file_id if File.objects.filter(id=file_id).exists() else None,
        query_text=query,
        top_k=top_k,
        duration_ms=None,  # you can restore timing if desired
        result_count=len(hits),
        result_json=hits,
    )
    return hits

'''
@shared_task(name="document_search.semantic_search_task")
def semantic_search_task(
    user_id: int,
    query: str,
    top_k: int,
    file_id: int | None,
    filters: dict | None,
) -> list[dict]:
    """
    Perform semantic search asynchronously.
    NOTE: View must call with **five** args (no extra list of accessible ids).
    """
    try:
        filters = filters or {}

        # Embed query
        embed_model = _get_model()
        query_vector = embed_model.encode([query])[0]

        # Milvus: ensure collection & user's partition
        collection = _ensure_collection()
        part_name = _partition_name(user_id)
        _ensure_partition(collection, part_name)
        collection.load(partition_names=[part_name])

        # Optional file constraint for Milvus ANN
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

        # Vector-hit file ids
        vector_file_ids = list({int(hit.entity.get("file_id")) for hit in results[0]})

        # 🔐 Compute accessible file IDs the same way as views
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()
        if user:
            accessible_file_ids = set(get_user_accessible_file_ids(user))
        else:
            # Fallback to ownership-only if user lookup fails
            accessible_file_ids = set(File.objects.filter(user_id=user_id).values_list("id", flat=True))

        if vector_file_ids:
            allowed_ids = set(vector_file_ids) & set(accessible_file_ids)
        else:
            return []

        if not allowed_ids:
            return []

        # Build additional filters
        q = Q(id__in=allowed_ids)

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

        files = File.objects.filter(q).prefetch_related("metadata")

        # Best (highest score) hit per file from vector results
        best_per_file: dict[int, tuple[str, float]] = {}
        for hit in results[0]:
            fid = int(hit.entity.get("file_id"))
            if fid not in allowed_ids:
                continue
            score = float(hit.score)
            chunk = hit.entity.get("chunk_text", "")
            prev = best_per_file.get(fid)
            if (not prev) or score > prev[1]:
                best_per_file[fid] = (chunk, score)

        out = []
        for f in files:
            md = f.metadata.first()
            chunk_text, score = best_per_file.get(f.id, ("", None))
            out.append({
                "file_id": f.id,
                "filename": f.filename,
                "file_size": f.file_size,
                "file_type": f.file_type,
                "document_type": getattr(f, "document_type", None),
                "created_at": f.created_at,
                "author": getattr(md, "author", None) if md else None,
                "keywords": getattr(md, "keywords", None) if md else None,
                "chunk_text": chunk_text,
                "score": score,
            })

        return out

    except Exception as e:
        LOGGER.error("Error in semantic search task: %s", str(e))
        return {"error": str(e)}
'''

@shared_task(name="document_search.semantic_search_task")
def semantic_search_task(
    user_id: int,
    query: str,
    top_k: int,
    file_id: int | None,
    filters: dict | None,
    project_id: str | None = None,
    service_id: str | None = None,
    generate_report: bool = False
) -> dict:
    """
    Perform semantic search asynchronously.

    Args:
        user_id: The user performing the search
        query: The search query
        top_k: Number of results to return
        file_id: Optional file ID to restrict search
        filters: Optional filters (created_from, created_to, author, project_id, service_id)
        project_id: Project ID for report registration (optional)
        service_id: Service ID for report registration (optional)
        generate_report: Whether to generate and register an HTML report

    Returns:
        Dict with results and optional report_file info
    """
    start_time = time.time()
    try:
        filters = filters or {}
        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return {"results": [], "count": 0}

        # 1) Access scope
        accessible_ids = set(get_user_accessible_file_ids(user))
        if file_id:
            accessible_ids &= {int(file_id)}
        if not accessible_ids:
            return {"results": [], "count": 0}

        # 2) Owner partitions to load
        owner_rows = (
            File.objects
            .filter(id__in=accessible_ids)
            .values("id", "user_id")  # or "user_id"
        )
        owner_partitions = {f"user_{row['user_id']}" for row in owner_rows}

        # 3) Embed
        embed_model = _get_model()
        qvec = embed_model.encode([query])[0]

        # 4) Search only allowed partitions + ids
        coll = _ensure_collection()
        for p in owner_partitions:
            _ensure_partition(coll, p)
        coll.load(partition_names=list(owner_partitions))

        id_list = ",".join(map(str, sorted(accessible_ids)))
        expr = f"file_id in [{id_list}]"

        results = coll.search(
            data=[qvec],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            expr=expr,
            output_fields=["file_id", "chunk_text"],
        )

        vector_file_ids = {int(hit.entity.get("file_id")) for hit in results[0]}
        allowed_ids = vector_file_ids & accessible_ids
        if not allowed_ids:
            return {"results": [], "count": 0}

        # 5) Apply optional metadata filters in Django
        q = Q(id__in=allowed_ids)
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

        files = File.objects.filter(q).prefetch_related("metadata")

        # best hit per file
        best = {}
        for hit in results[0]:
            fid = int(hit.entity.get("file_id"))
            if fid not in allowed_ids:
                continue
            score = float(hit.score)
            chunk = hit.entity.get("chunk_text", "")
            if (fid not in best) or (score > best[fid][1]):
                best[fid] = (chunk, score)

        out = []
        for f in files:
            md = f.metadata.first()
            chunk_text, score = best.get(f.id, ("", None))
            out.append({
                "file_id": f.id,
                "filename": f.filename,
                "file_size": f.file_size,
                "file_type": f.file_type,
                "document_type": getattr(f, "document_type", None),
                "created_at": str(f.created_at) if f.created_at else None,
                "author": getattr(md, "author", None) if md else None,
                "keywords": getattr(md, "keywords", None) if md else None,
                "chunk_text": chunk_text,
                "score": score,
            })

        execution_time = time.time() - start_time

        response = {
            "results": out,
            "count": len(out),
            "query": query,
            "execution_time_seconds": round(execution_time, 2)
        }

        # Generate and register report if requested
        if generate_report and project_id and service_id:
            try:
                # Create a Run instance for the report
                from django.contrib.contenttypes.models import ContentType
                run = Run.objects.create(
                    user=user,
                    project_id=project_id,
                    service_id=service_id,
                    status="completed",
                    result_json=response
                )

                report_info = generate_and_register_service_report(
                    service_name="Semantic Search",
                    service_id="ai-semantic-search",
                    vertical="AI Services",
                    response_data=response,
                    user=user,
                    run=run,
                    project_id=project_id,
                    service_id_folder=service_id,
                    folder_name="semantic-search-results",
                    query=query,
                    execution_time_seconds=execution_time,
                    additional_metadata={
                        "top_k": top_k,
                        "file_id_filter": file_id,
                        "filters_applied": bool(filters)
                    }
                )
                response["report_file"] = report_info
                LOGGER.info(f"✅ Generated semantic search report: {report_info.get('filename')}")
            except Exception as report_error:
                LOGGER.warning(f"Failed to generate report: {report_error}")
                response["report_error"] = str(report_error)

        return response

    except Exception as e:
        LOGGER.error("Error in semantic search task: %s", str(e))
        return {"error": str(e), "results": [], "count": 0}


# ───────────── Optional alias for semantic clarity ─────────────
process_file_for_search = index_file

