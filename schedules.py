"""
File-based storage for report schedules (no database permissions required).
Schedules are stored in data/schedules.json.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_FILE = os.path.join(_DATA_DIR, "schedules.json")


def _load() -> List[Dict[str, Any]]:
    if not os.path.isfile(_FILE):
        return []
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(schedules: List[Dict[str, Any]]) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(schedules, f, indent=2)


def list_schedules() -> List[Dict[str, Any]]:
    raw = _load()
    return [
        {
            "id": s["id"],
            "report_key": s["report_key"],
            "frequency": s["frequency"],
            "created_at_utc": s.get("created_at_utc"),
            "created_at_display": _format_display(s.get("created_at_utc")),
        }
        for s in raw
    ]


def _format_display(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except (ValueError, TypeError):
        return str(iso_str) if iso_str else "—"


def add_schedule(report_key: str, frequency: str) -> str:
    schedule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    schedules = _load()
    schedules.insert(
        0,
        {
            "id": schedule_id,
            "report_key": report_key,
            "frequency": frequency,
            "created_at_utc": now,
        },
    )
    _save(schedules)
    return schedule_id


def delete_schedule(schedule_id: str) -> None:
    schedules = [s for s in _load() if s.get("id") != schedule_id]
    _save(schedules)
