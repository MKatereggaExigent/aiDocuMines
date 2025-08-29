# insights_hub/providers/core_provider.py
from __future__ import annotations
from datetime import date
from typing import Dict, Any
from django.db.models import Count, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from insights_hub.registry import register
from core.models import File, Storage, Metadata

@register
def core_provider(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    ctx: { 'user': User, 'since': datetime|None, 'until': datetime|None, 'project_id': str|None, 'service_id': str|None }
    """
    user = ctx["user"]
    since = ctx.get("since")
    until = ctx.get("until") or timezone.now()

    files_q = File.objects.filter(user=user)
    if since:
        files_q = files_q.filter(created_at__date__gte=since.date())
    if until:
        files_q = files_q.filter(created_at__date__lte=until.date())

    if ctx.get("project_id"):
        files_q = files_q.filter(project_id=ctx["project_id"])
    if ctx.get("service_id"):
        files_q = files_q.filter(service_id=ctx["service_id"])

    total_files = files_q.count()

    # "Modified" = updated_at > created_at OR status != Pending
    modified_q = files_q.filter(Q(updated_at__gt=F("created_at")) | ~Q(status="Pending"))
    modified_files = modified_q.count()

    # Pending
    pending_files = files_q.filter(status__in=["Pending", "Processing"]).count()

    # Encrypted (from Metadata flags)
    meta_q = Metadata.objects.filter(file__user=user, file__in=files_q.values("id"))
    enc_files = meta_q.filter(Q(is_encrypted=True) | Q(encrypted=True)).values("file_id").distinct().count()

    # Doc type / extension distribution
    doc_types = (
        files_q.values("document_type", "extension")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    doc_type_distribution = [
        {"type": (x["document_type"] or x["extension"] or "Unknown"), "count": x["count"]}
        for x in doc_types
    ]

    # Volume trend by created_at day
    vol = (
        files_q.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    volume_trend = [{"date": v["day"], "value": v["count"]} for v in vol]

    # Storages
    stor = (
        File.objects.filter(user=user)
        .values("storage__upload_storage_location")
        .annotate(files=Count("id"))
        .order_by("storage__upload_storage_location")
    )
    storages = [{
        "name": s["storage__upload_storage_location"] or "Unassigned",
        "files": s["files"],
        "encrypted": 0,   # filled by Metadata below
        "risk": 0,        # anonymizer provider may fill risk
    } for s in stor]

    # Encrypted per storage
    enc_per_storage = (
        meta_q.filter(Q(is_encrypted=True) | Q(encrypted=True))
        .values("file__storage__upload_storage_location")
        .annotate(enc=Count("file_id", distinct=True))
    )
    enc_map = {r["file__storage__upload_storage_location"]: r["enc"] for r in enc_per_storage}
    for s in storages:
        s["encrypted"] = enc_map.get(s["name"], 0)

    # Recent files (last 20)
    recent = (
        File.objects.filter(user=user)
        .order_by(F("updated_at").desc(nulls_last=True), F("created_at").desc(nulls_last=True))
        .values("id", "filename", "project_id", "file_size", "updated_at", "status")[:20]
    )
    recent_files = [{
        "id": r["id"],
        "name": r["filename"],
        "project": r["project_id"],
        "size_bytes": r["file_size"],
        "modified_at": r["updated_at"],
        "status": r["status"],
        "tags": [],
    } for r in recent]

    return {
        "totals": {
            "files": total_files,
            "modified": modified_files,
            "pending": pending_files,
            "encrypted": enc_files,
        },
        "doc_type_distribution": doc_type_distribution,
        "volume_trend": volume_trend,
        "storages": storages,
        "recent_files": recent_files,
    }

