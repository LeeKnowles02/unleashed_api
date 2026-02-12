from typing import Any, Optional
import os

def db_enabled() -> bool:
    return bool(os.getenv("AZURE_SQL_SERVER") and os.getenv("AZURE_SQL_DB") and os.getenv("AZURE_SQL_USER") and os.getenv("AZURE_SQL_PASSWORD"))

def try_insert_raw(
    *,
    run_id: Optional[str],
    company_id: Optional[str],
    endpoint: str,
    http_status: Optional[int],
    payload_obj: Any,
    request_url: Optional[str] = None,
    page_number: Optional[int] = None,
    api_cursor: Optional[str] = None,
) -> None:
    if not run_id:
        return
    if not db_enabled():
        return

    try:
        from db import insert_raw_payload 
        insert_raw_payload(
            run_id=run_id,
            company_id=company_id,
            endpoint=endpoint,
            http_status=http_status,
            payload_obj=payload_obj,
            request_url=request_url,
            page_number=page_number,
            api_cursor=api_cursor,
        )
    except Exception:
        return
