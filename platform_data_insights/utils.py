# platform_data_insights/utils.py

from core.models import File, Metadata, Run, Storage
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

def calculate_user_insights(user):
    """
    Perform all data aggregation for a single user.
    Returns a single dict with all insights data.
    """

    # --- pending / failed documents
    pending_files = File.objects.filter(
        user=user,
        status__in=["Pending", "Failed"]
    ).values("id", "filename", "status", "file_size", "created_at")

    # --- recent documents
    # recent_files = File.objects.filter(user=user).order_by("-created_at")[:10].values(
    #     "id", "filename", "status", "created_at"
    # )

    recent_files_raw = File.objects.filter(user=user).order_by("-created_at")[:10].values(
        "id", "filename", "status", "created_at"
    )
    recent_files = []
    for f in recent_files_raw:
        f["created_at"] = f["created_at"].isoformat() if f["created_at"] else None
        recent_files.append(f)

    # --- document type distribution
    doc_type_distribution = (
        File.objects.filter(user=user)
        .values("document_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # --- document volume trend
    thirty_days_ago = timezone.now() - timedelta(days=30)
    volume_trend = (
        File.objects.filter(user=user, created_at__gte=thirty_days_ago)
        .extra(select={"date": "date(created_at)"})
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # --- encrypted documents
    encrypted_docs_count = Metadata.objects.filter(file__user=user, is_encrypted=True).count()

    # --- flagged docs
    flagged_docs_count = File.objects.filter(user=user, status="Failed").count()

    # --- avg document length
    avg_pages = Metadata.objects.filter(file__user=user).aggregate(
        avg_pages=Avg("page_count")
    )["avg_pages"] or 0

    # --- duplicate files
    duplicates = (
        File.objects.filter(user=user)
        .values("md5_hash", "filename")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )
    duplicate_list = [
        {"filename": d["filename"], "count": d["count"]}
        for d in duplicates
    ]

    # --- metadata compliance
    issues = []
    meta_qs = Metadata.objects.filter(file__user=user)
    if meta_qs.filter(author__isnull=True).exists():
        issues.append("Missing author in some documents.")
    if meta_qs.filter(title__isnull=True).exists():
        issues.append("Missing title in some documents.")
    if meta_qs.filter(page_count__lte=0).exists():
        issues.append("Documents with 0 pages detected.")

    # --- storage locations
    storages = list(Storage.objects.filter(user=user).values(
        "upload_storage_location", "output_storage_location"
    ))

    # --- avg processing time
    avg_processing_time = None
    runs = Run.objects.filter(user=user).values("created_at", "updated_at")
    if runs:
        durations = []
        for r in runs:
            if r["updated_at"] and r["created_at"]:
                duration = (r["updated_at"] - r["created_at"]).total_seconds()
                durations.append(duration)
        if durations:
            avg_processing_time = sum(durations) / len(durations)

    # --- delayed files
    delayed_files_count = File.objects.filter(
        user=user,
        status="Processing",
        created_at__lt=timezone.now() - timedelta(hours=1)
    ).count()

    # --- total cost
    total_cost = Run.objects.filter(user=user).aggregate(
        total=Sum("cost")
    )["total"] or 0

    return {
        "pending_files": list(pending_files),
        "recent_files": list(recent_files),
        "doc_type_distribution": list(doc_type_distribution),
        "volume_trend": list(volume_trend),
        "encrypted_docs_count": encrypted_docs_count,
        "flagged_docs_count": flagged_docs_count,
        "avg_pages": avg_pages,
        "duplicates": duplicate_list,
        "metadata_issues": issues,
        "storages": storages,
        "avg_processing_time": avg_processing_time,
        "delayed_files_count": delayed_files_count,
        "total_cost": float(total_cost),
    }

