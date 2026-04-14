from typing import Any, Optional
import os
import time

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
        from integration_log_writer import log_error, log_info

        items = payload_obj.get("Items") if isinstance(payload_obj, dict) else None
        n_items = len(items) if isinstance(items, list) else None
        log_info(
            f"Raw API payload write starting: table raw.api_payload, endpoint='{endpoint}', page_number={page_number}, "
            f"run_id={run_id}, http_status={http_status}, Items_count={n_items}.",
            integration_name="azure_sql",
            module_name="exports.utils_db",
            function_name="try_insert_raw",
            event_type="raw_payload_write_started",
            action="insert",
            step_name="raw.api_payload",
            entity_name="raw.api_payload",
            endpoint=endpoint,
            status="STARTED",
            record_count=n_items,
            request_url=request_url,
            detail="Full JSON stored in raw.api_payload; integration_log stores summaries only.",
        )
    except Exception:
        pass

    t0 = time.perf_counter()
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
        ms = int((time.perf_counter() - t0) * 1000)
        try:
            from integration_log_writer import log_info

            log_info(
                f"Raw API payload write completed: raw.api_payload for endpoint '{endpoint}' page {page_number} in {ms} ms.",
                integration_name="azure_sql",
                module_name="exports.utils_db",
                function_name="try_insert_raw",
                event_type="raw_payload_write_completed",
                action="insert",
                step_name="raw.api_payload",
                entity_name="raw.api_payload",
                endpoint=endpoint,
                status="SUCCESS",
                duration_ms=ms,
                request_url=request_url,
            )
        except Exception:
            pass
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        try:
            from integration_log_writer import log_error

            log_error(
                f"Raw API payload write failed: raw.api_payload for endpoint '{endpoint}' page {page_number} after {ms} ms.",
                exc=exc,
                integration_name="azure_sql",
                module_name="exports.utils_db",
                function_name="try_insert_raw",
                event_type="raw_payload_write_failed",
                action="insert",
                step_name="raw.api_payload",
                entity_name="raw.api_payload",
                endpoint=endpoint,
                duration_ms=ms,
                request_url=request_url,
                detail="Export continues; only raw audit trail is missing for this page. Check DB permissions and raw.api_payload schema.",
            )
        except Exception:
            pass
        return
