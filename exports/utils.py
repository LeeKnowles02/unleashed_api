from datetime import datetime, timezone
from typing import Optional

def parse_unleashed_dotnet_date(value: Optional[str]) -> Optional[datetime]:
    """
    Converts '/Date(1700000000000)/' -> datetime (naive, UTC)
    Excel/openpyxl require tzinfo=None.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        ms = int(value.strip("/").replace("Date(", "").replace(")", ""))
        dt_utc = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        return dt_utc.replace(tzinfo=None)  # <- IMPORTANT: remove timezone
    except Exception:
        return None
