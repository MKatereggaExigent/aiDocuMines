# document_structures/utils.py

import os
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text
from unstructured.partition.auto import partition

from document_structures import models
from core.models import File, Run, User

from django.db import transaction

from sentence_transformers import SentenceTransformer
import numpy as np

import logging

logger = logging.getLogger(__name__)

# Load once for efficiency if embeddings enabled
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def safe_metadata_to_dict(obj):
    """
    Recursively converts unstructured objects (e.g. CoordinatesMetadata)
    into JSON-safe types for storage.
    """
    if obj is None:
        return None
    if hasattr(obj, "to_dict"):
        return safe_metadata_to_dict(obj.to_dict())
    elif hasattr(obj, "dict"):
        return safe_metadata_to_dict(obj.dict())
    elif isinstance(obj, dict):
        return {k: safe_metadata_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [safe_metadata_to_dict(x) for x in obj]
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        # Fallback to string
        return str(obj)


def embed_text(text: str) -> list[float]:
    """
    Convert text to embedding vector using sentence-transformers.
    """
    if not text.strip():
        return None
    embedding = EMBEDDING_MODEL.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def run_partition(file: File, partition_strategy: str) -> list:
    """
    Run the unstructured partitioning based on the selected strategy.
    Returns a list of unstructured elements.
    """
    file_path = file.filepath
    logger.warning(f"→ Partitioning file: {file_path} | strategy={partition_strategy}")

    if partition_strategy == "partition_pdf":
        elements = partition_pdf(filename=file_path)
    elif partition_strategy == "partition_text":
        elements = partition_text(filename=file_path)
    elif partition_strategy == "partition_auto":
        elements = partition(filename=file_path)
    else:
        raise ValueError(f"Unknown partition strategy: {partition_strategy}")

    logger.warning(f"✅ Partition produced {len(elements)} elements.")
    return elements


@transaction.atomic
def process_document_structures(
    file: File,
    run: Run,
    user: User,
    partition_strategy: str = "partition_auto",
    store_embeddings: bool = True,
) -> models.DocumentStructureRun:
    """
    Main entry point to:
    - run partition
    - save DocumentStructureRun
    - save DocumentElements, including any tables or hierarchy
    """

    logger.warning(f"📝 Starting processing of file_id={file.id}, run_id={run.run_id}")

    # Create the DocumentStructureRun
    ds_run = models.DocumentStructureRun.objects.create(
        run=run,
        file=file,
        user=user,
        partition_strategy=partition_strategy,
        status="Processing",
    )

    try:
        elements = run_partition(file, partition_strategy)
    except Exception as e:
        ds_run.status = "Failed"
        ds_run.error_message = str(e)
        ds_run.save()
        logger.error(f"🔥 Partitioning failed: {e}")
        raise

    logger.warning(f"→ About to process {len(elements)} elements.")

    element_objects = []
    table_objects = []
    cell_objects = []
    parent_map = {}
    order_counter = 0

    for el in elements:
        order_counter += 1

        el_type = el.category if hasattr(el, "category") else None
        el_text = el.text if hasattr(el, "text") else None
        el_metadata = safe_metadata_to_dict(el.metadata) if hasattr(el, "metadata") else None
        page_num = None
        coordinates = None

        # Extract page number if available
        if hasattr(el, "metadata") and hasattr(el.metadata, "page_number"):
            page_num = el.metadata.page_number

        # Extract coordinates
        if hasattr(el, "metadata") and hasattr(el.metadata, "coordinates"):
            coords = el.metadata.coordinates
            if coords is not None:
                coordinates = safe_metadata_to_dict(coords)

        # Compute embedding if desired
        embedding_vec = None
        if store_embeddings and el_text:
            embedding_vec = embed_text(el_text)

        de = models.DocumentElement(
            run=ds_run,
            element_type=el_type,
            text=el_text,
            metadata=el_metadata,
            parent=None,
            page_number=page_num,
            coordinates=coordinates,
            order=order_counter,
            embedding=embedding_vec,
        )

        element_objects.append(de)

        logger.warning(f"✅ Element {order_counter}: Type={el_type} | Text='{(el_text or '')[:80]}'")

        parent_map[id(el)] = de

        if el_type == "Table" and hasattr(el, "metadata") and hasattr(el.metadata, "text_as_html"):
            html = el.metadata.text_as_html
            csv_text = el.metadata.text_as_csv if hasattr(el.metadata, "text_as_csv") else None
            json_data = el.metadata.table_as_json if hasattr(el.metadata, "table_as_json") else None

            dt = models.DocumentTable.objects.create(
                run=ds_run,
                page_number=page_num,
                order=order_counter,
                html=html,
                csv=csv_text,
                json=json_data,
            )
            table_objects.append(dt)

            if json_data:
                for row_idx, row in enumerate(json_data):
                    for col_idx, cell_text in enumerate(row):
                        cell = models.DocumentTableCell(
                            table=dt,
                            row_idx=row_idx,
                            col_idx=col_idx,
                            text=str(cell_text),
                        )
                        cell_objects.append(cell)

    # Bulk insert elements
    if element_objects:
        try:
            elements = models.DocumentElement.objects.bulk_create(element_objects)
            logger.warning(f"✅ Saved {len(elements)} DocumentElement rows to DB.")
        except Exception as e:
            logger.error(f"🔥 bulk_create for DocumentElement failed: {e}")
            raise
    else:
        logger.warning("⚠️ No elements to save.")

    # Parent relationships
    updates = []
    for el in elements:
        original_el = element_objects[elements.index(el)]
        if hasattr(original_el, "parent") and original_el.parent:
            parent_obj = parent_map.get(id(original_el.parent))
            if parent_obj:
                el.parent = parent_obj
                updates.append(el)

    if updates:
        try:
            models.DocumentElement.objects.bulk_update(updates, ["parent"])
            logger.warning(f"✅ Updated parent relationships for {len(updates)} elements.")
        except Exception as e:
            logger.error(f"🔥 bulk_update for parent relationships failed: {e}")
            raise

    # Bulk save table cells
    if cell_objects:
        try:
            models.DocumentTableCell.objects.bulk_create(cell_objects)
            logger.warning(f"✅ Saved {len(cell_objects)} DocumentTableCell rows.")
        except Exception as e:
            logger.error(f"🔥 bulk_create for table cells failed: {e}")
            raise

    ds_run.status = "Completed"
    ds_run.error_message = None
    ds_run.save()

    logger.warning(f"✅ DocumentStructureRun {ds_run.id} marked as Completed.")

    return ds_run


def compare_document_runs(run1: models.DocumentStructureRun, run2: models.DocumentStructureRun):
    """
    Computes lexical and semantic similarity between two document structure runs.
    Stores DocumentComparison record.
    """

    logger.warning(f"🔍 Comparing runs {run1.id} vs {run2.id}")

    elems1 = models.DocumentElement.objects.filter(run=run1).order_by("order")
    elems2 = models.DocumentElement.objects.filter(run=run2).order_by("order")

    text1 = " ".join([el.text for el in elems1 if el.text])
    text2 = " ".join([el.text for el in elems2 if el.text])

    lexical_sim = lexical_similarity_score(text1, text2)
    semantic_sim = semantic_similarity_score(text1, text2)

    comparison = models.DocumentComparison.objects.create(
        run_1=run1,
        run_2=run2,
        lexical_similarity=lexical_sim,
        semantic_similarity=semantic_sim,
        deviation_report={},
        status="Completed"
    )

    logger.warning(f"✅ Comparison complete. Lexical={lexical_sim:.3f}, Semantic={semantic_sim:.3f}")

    return comparison


def lexical_similarity_score(text1: str, text2: str) -> float:
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    if not union:
        return 0.0

    return len(intersection) / len(union)


def semantic_similarity_score(text1: str, text2: str) -> float:
    if not text1.strip() or not text2.strip():
        return 0.0

    emb1 = embed_text(text1)
    emb2 = embed_text(text2)

    if emb1 is None or emb2 is None:
        return 0.0

    v1 = np.array(emb1)
    v2 = np.array(emb2)

    cosine_sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    return cosine_sim

