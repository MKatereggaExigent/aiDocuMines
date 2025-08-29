# insights_hub/providers/anonymizer_provider.py
from __future__ import annotations
from typing import Dict, Any
from django.db.models import Q, Count, F

from insights_hub.registry import register
from document_anonymizer.models import Anonymize, AnonymizationRun

@register
def anonymizer_provider(ctx: Dict[str, Any]) -> Dict[str, Any]:
    user = ctx["user"]

    # Scope by user via original_file.user
    base = Anonymize.objects.filter(original_file__user=user, is_active=True)

    # Filters
    if ctx.get("project_id"):
        base = base.filter(original_file__project_id=ctx["project_id"])
    if ctx.get("service_id"):
        base = base.filter(original_file__service_id=ctx["service_id"])

    # Completed anonymizations
    anonymized_docs = base.filter(status="Completed").values("original_file_id").distinct().count()

    # Risk (risk_score >= 0.7 or risk_level in {high, critical})
    risk_q = base.filter(Q(risk_score__gte=0.7) | Q(risk_level__in=["high", "critical"]))
    files_at_risk = risk_q.values("original_file_id").distinct().count()

    # Flagged = medium risk (0.4–0.69) or risk_level == "medium"
    flagged_q = base.filter(
        Q(risk_level="medium") | (Q(risk_score__gte=0.4) & Q(risk_score__lt=0.7))
    )
    flagged = flagged_q.values("original_file_id").distinct().count()

    # Alerts: top 10 risky items
    top_risky = risk_q.order_by(F("risk_score").desc(nulls_last=True)).select_related("original_file")[:10]
    alerts = []
    for a in top_risky:
        alerts.append({
            "id": str(a.id),
            "level": "critical" if (a.risk_score or 0) >= 0.85 or a.risk_level == "critical" else "warning",
            "title": f"High risk document",
            "message": f"{a.original_file.filename} risk={a.risk_level or a.risk_score}",
            "created_at": a.updated_at,
            "project": a.original_file.project_id,
            "file_id": a.original_file_id,
            "rule": "anonymizer_risk"
        })

    # Pending processing = anonymization runs in Pending/Processing for this user's files
    runs = AnonymizationRun.objects.filter(
        anonymized_files__original_file__user=user
    ).distinct()
    pending_runs = runs.filter(status__in=["Pending", "Processing"]).count()

    # Risk per storage (augment storages later)
    risk_per_storage = base.filter(
        Q(risk_score__gte=0.7) | Q(risk_level__in=["high","critical"])
    ).values("original_file__storage__upload_storage_location").annotate(
        risk=Count("original_file_id", distinct=True)
    )
    risk_map = {r["original_file__storage__upload_storage_location"]: r["risk"] for r in risk_per_storage}

    return {
        "totals": {
            "anonymized": anonymized_docs,
            "atRisk": files_at_risk,
            "flagged": flagged,
            "pending": pending_runs,  # contributes to global 'pending'
        },
        "alerts": alerts,
        "storages_risk_map": risk_map,
    }

