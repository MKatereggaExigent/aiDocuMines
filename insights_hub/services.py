# insights_hub/services.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from django.utils import timezone
from .registry import providers

@dataclass
class DateRange:
    since: Optional[datetime]
    until: Optional[datetime]

def _parse_range(from_str: Optional[str], to_str: Optional[str]) -> DateRange:
    def parse_one(s: Optional[str]) -> Optional[datetime]:
        if not s: return None
        try:
            dt = datetime.fromisoformat(s.replace("Z","+00:00"))
        except Exception:
            return None
        if timezone.is_naive(dt): dt = timezone.make_aware(dt)
        return dt

    until = parse_one(to_str) or timezone.now()
    since = parse_one(from_str) or (until - timedelta(days=30))
    return DateRange(since, until)

def _merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow merge for our shape."""
    out = dict(a)
    # totals
    ta = a.get("totals", {}) or {}
    tb = b.get("totals", {}) or {}
    totals = dict(ta)
    for k, v in tb.items():
        totals[k] = (totals.get(k, 0) or 0) + (v or 0)
    out["totals"] = totals

    # lists
    for key in ["volume_trend", "doc_type_distribution", "recent_files", "alerts", "storages"]:
        a_list = out.get(key, []) or []
        b_list = b.get(key, []) or []
        out[key] = a_list + b_list

    # special map augmentation for storages risk
    risk_map = b.get("storages_risk_map")
    if risk_map:
        # ensure storages list exists
        out.setdefault("storages", [])
        name_to_idx = {s["name"]: i for i, s in enumerate(out["storages"]) if "name" in s}
        for name, risk in risk_map.items():
            idx = name_to_idx.get(name)
            if idx is not None:
                out["storages"][idx]["risk"] = (out["storages"][idx].get("risk", 0) or 0) + (risk or 0)
            else:
                out["storages"].append({"name": name or "Unassigned", "files": 0, "encrypted": 0, "risk": risk})

    return out

def compute_insights(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    context: {'user', 'from', 'to', 'project_id', 'service_id'}
    """
    rng = _parse_range(context.get("from"), context.get("to"))
    ctx = {
        "user": context["user"],
        "since": rng.since,
        "until": rng.until,
        "project_id": context.get("project_id"),
        "service_id": context.get("service_id"),
    }

    agg: Dict[str, Any] = {
        "totals": {},
        "volume_trend": [],
        "doc_type_distribution": [],
        "recent_files": [],
        "alerts": [],
        "storages": [],
        "last_computed_at": timezone.now(),
    }

    for p in providers():
        try:
            res = p(ctx) or {}
            agg = _merge(agg, res)
        except Exception as e:
            # don't fail the whole dashboard because one provider failed
            agg["alerts"].append({
                "id": f"provider-error-{p.__name__}",
                "level": "warning",
                "title": f"Provider {p.__name__} failed",
                "message": str(e),
                "created_at": timezone.now(),
                "project": None,
                "file_id": None,
                "rule": "provider_error"
            })

    # derive safe
    files = agg["totals"].get("files", 0) or 0
    at_risk = agg["totals"].get("atRisk", 0) or 0
    agg["totals"]["safe"] = max(files - at_risk, 0)

    return agg

