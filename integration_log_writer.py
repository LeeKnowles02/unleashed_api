"""
Detailed database integration logging for Unleashed Runner.

Writes verbose, structured rows to unleashed.integration_log.
Never raises to callers; failures are swallowed after optional stderr print.

Requires table from unleashed_schema/integration_log.sql (or setup script).
"""
from __future__ import annotations

import contextvars
import getpass
import json
import os
import re
import socket
import sys
import time
import traceback
import uuid
from typing import Any, Dict, Optional

# --- Context (correlation across a request / export run) ---
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "integration_correlation_id", default=None
)
_run_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "integration_run_id", default=None
)
_company_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "integration_company_id", default=None
)

PROJECT_NAME = "Unleashed_Runner"
SOURCE_SYSTEM = "Unleashed_API"

_SENSITIVE_HEADER_KEYS = frozenset(
    k.lower()
    for k in (
        "authorization",
        "api-auth-signature",
        "api-auth-id",
        "x-api-key",
        "cookie",
        "set-cookie",
    )
)

_TABLE_EXISTS_CACHE: Optional[bool] = None


def set_correlation_id(value: Optional[str] = None) -> str:
    cid = value or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def set_run_context(run_id: Optional[str], company_id: Optional[str] = None) -> None:
    _run_id.set(run_id)
    if company_id is not None:
        _company_id.set(company_id)


def get_run_id() -> Optional[str]:
    return _run_id.get()


def get_company_id() -> Optional[str]:
    return _company_id.get()


def clear_run_context() -> None:
    _run_id.set(None)
    _company_id.set(None)


def clear_correlation_id() -> None:
    _correlation_id.set(None)


def clear_integration_request_context() -> None:
    """Reset correlation + run context after each HTTP request (Flask teardown)."""
    clear_correlation_id()
    clear_run_context()


def mask_secrets_in_string(text: str, max_len: int = 8000) -> str:
    if not text:
        return text
    out = text
    patterns = [
        (re.compile(r"(?i)(api[_-]?key|apikey|password|pwd|secret|token)\s*[=:]\s*[^\s&]+"), r"\1=***"),
        (re.compile(r"(?i)(Pwd=)([^;]+)"), r"\1***"),
        (re.compile(r"(?i)(api-auth-signature=)([^&\s]+)"), r"\1***"),
    ]
    for pat, repl in patterns:
        out = pat.sub(repl, out)
    if len(out) > max_len:
        return out[:max_len] + f"...(truncated, total_len={len(out)})"
    return out


def safe_headers_json(headers: Optional[Dict[str, Any]]) -> Optional[str]:
    if not headers:
        return None
    safe: Dict[str, str] = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in _SENSITIVE_HEADER_KEYS or "signature" in lk or "auth" in lk:
            safe[k] = "***"
        else:
            safe[k] = str(v)[:500]
    try:
        return json.dumps(safe, ensure_ascii=False)
    except Exception:
        return str(safe)[:4000]


def summarize_payload(obj: Any, max_len: int = 4000) -> Optional[str]:
    if obj is None:
        return None
    try:
        if isinstance(obj, dict):
            items = obj.get("Items")
            pag = obj.get("Pagination")
            parts = []
            if isinstance(pag, dict):
                parts.append(f"Pagination={pag}")
            if isinstance(items, list):
                parts.append(f"Items_count={len(items)}")
            base = "; ".join(parts) if parts else ""
            if base and len(base) <= max_len:
                return base
        s = json.dumps(obj, default=str, ensure_ascii=False)
        return mask_secrets_in_string(s, max_len=max_len)
    except Exception:
        return mask_secrets_in_string(str(obj)[:max_len], max_len=max_len)


def safe_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return mask_secrets_in_string(url, max_len=2048)


def _db_logging_enabled() -> bool:
    return bool(
        os.getenv("AZURE_SQL_SERVER")
        and os.getenv("AZURE_SQL_DB")
        and os.getenv("AZURE_SQL_USER")
        and os.getenv("AZURE_SQL_PASSWORD")
    )


def _integration_log_table_exists() -> bool:
    global _TABLE_EXISTS_CACHE
    if _TABLE_EXISTS_CACHE is not None:
        return _TABLE_EXISTS_CACHE
    if not _db_logging_enabled():
        _TABLE_EXISTS_CACHE = False
        return False
    try:
        from db import get_conn

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT OBJECT_ID('unleashed.integration_log', 'U')")
            _TABLE_EXISTS_CACHE = cur.fetchone()[0] is not None
    except Exception:
        _TABLE_EXISTS_CACHE = False
    return _TABLE_EXISTS_CACHE


def _reset_table_cache() -> None:
    global _TABLE_EXISTS_CACHE
    _TABLE_EXISTS_CACHE = None


def log_event(
    log_level: str,
    message: str,
    *,
    integration_name: Optional[str] = None,
    module_name: Optional[str] = None,
    function_name: Optional[str] = None,
    event_type: Optional[str] = None,
    run_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    company_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    entity_name: Optional[str] = None,
    action: Optional[str] = None,
    step_name: Optional[str] = None,
    status: Optional[str] = None,
    detail: Optional[str] = None,
    payload_summary: Optional[str] = None,
    record_count: Optional[int] = None,
    duration_ms: Optional[int] = None,
    http_status_code: Optional[int] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    stack_trace: Optional[str] = None,
    request_url: Optional[str] = None,
    request_method: Optional[str] = None,
    request_params: Optional[str] = None,
    request_headers_safe: Optional[str] = None,
    response_summary: Optional[str] = None,
    response_body_safe: Optional[str] = None,
) -> None:
    if not _db_logging_enabled():
        return
    if not _integration_log_table_exists():
        return

    rid = run_id if run_id is not None else get_run_id()
    cid = correlation_id if correlation_id is not None else get_correlation_id()
    comp = company_id if company_id is not None else get_company_id()

    row = {
        "project_name": PROJECT_NAME,
        "integration_name": integration_name,
        "source_system": SOURCE_SYSTEM,
        "module_name": module_name,
        "function_name": function_name,
        "log_level": (log_level or "INFO")[:16],
        "event_type": event_type,
        "run_id": rid,
        "correlation_id": cid,
        "company_id": comp,
        "endpoint": endpoint,
        "entity_name": entity_name,
        "action": action,
        "step_name": step_name,
        "status": status,
        "message": message,
        "detail": detail,
        "payload_summary": payload_summary,
        "record_count": record_count,
        "duration_ms": duration_ms,
        "http_status_code": http_status_code,
        "error_type": error_type,
        "error_message": error_message,
        "stack_trace": stack_trace,
        "request_url": safe_url(request_url),
        "request_method": request_method,
        "request_params": mask_secrets_in_string(request_params) if request_params else None,
        "request_headers_safe": request_headers_safe,
        "response_summary": response_summary,
        "response_body_safe": mask_secrets_in_string(response_body_safe) if response_body_safe else None,
        "machine_name": socket.gethostname()[:256],
        "environment": (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "local")[:64],
        "created_by": (getpass.getuser() or "unknown")[:256],
    }

    cols = [k for k, v in row.items() if v is not None]
    if not cols:
        return
    placeholders = ", ".join(["?"] * len(cols))
    quoted = ", ".join(f"[{c}]" for c in cols)
    values = [row[c] for c in cols]

    try:
        from db import get_conn

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO unleashed.integration_log ({quoted}) VALUES ({placeholders})",
                *values,
            )
            conn.commit()
    except Exception:
        _reset_table_cache()
        return


def log_debug(
    message: str,
    **kwargs: Any,
) -> None:
    log_event("DEBUG", message, **kwargs)


def log_info(message: str, **kwargs: Any) -> None:
    log_event("INFO", message, **kwargs)


def log_warning(message: str, **kwargs: Any) -> None:
    log_event("WARNING", message, **kwargs)


def log_error(
    message: str,
    *,
    exc: Optional[BaseException] = None,
    **kwargs: Any,
) -> None:
    et = kwargs.pop("error_type", None)
    em = kwargs.pop("error_message", None)
    st = kwargs.pop("stack_trace", None)
    status = kwargs.pop("status", None) or "FAIL"
    if exc is not None:
        et = et or type(exc).__name__
        em = em or str(exc)
        st = st or traceback.format_exc()
    log_event(
        "ERROR",
        message,
        error_type=et,
        error_message=em,
        stack_trace=st,
        status=status,
        **kwargs,
    )


def log_db_connect_attempt() -> None:
    log_info(
        "Attempting Azure SQL connection using configured ODBC settings (credentials not logged).",
        integration_name="azure_sql",
        module_name="integration_log_writer",
        function_name="log_db_connect_attempt",
        event_type="database_connection_attempt",
        action="connect",
        step_name="pyodbc.connect",
        status="STARTED",
        detail="Uses db.get_conn() with Driver 18; server/database/user from environment variables only.",
    )


def log_db_connect_result(success: bool, duration_ms: int, error: Optional[BaseException] = None) -> None:
    if success:
        log_info(
            f"Azure SQL connection succeeded in {duration_ms} ms; SELECT 1 returned OK.",
            integration_name="azure_sql",
            module_name="integration_log_writer",
            function_name="log_db_connect_result",
            event_type="database_connection_success",
            action="connect",
            step_name="validate_connection",
            status="SUCCESS",
            duration_ms=duration_ms,
        )
    else:
        log_error(
            f"Azure SQL connection failed after {duration_ms} ms.",
            exc=error,
            integration_name="azure_sql",
            module_name="integration_log_writer",
            function_name="log_db_connect_result",
            event_type="database_connection_failure",
            action="connect",
            step_name="validate_connection",
            status="FAIL",
            duration_ms=duration_ms,
            detail="Verify AZURE_SQL_* env vars, firewall rules, and ODBC Driver 18. Next: test with SSMS or sqlcmd.",
        )


def ping_database() -> bool:
    """Returns True if SELECT 1 succeeds. Logs attempt and outcome."""
    if not _db_logging_enabled():
        log_warning(
            "Database logging skipped ping: AZURE_SQL_* environment variables not fully set.",
            integration_name="azure_sql",
            module_name="integration_log_writer",
            function_name="ping_database",
            event_type="database_connection_skipped",
            action="connect",
            status="SKIPPED",
            detail="Set AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD to enable DB and integration_log.",
        )
        return False
    log_db_connect_attempt()
    t0 = time.perf_counter()
    try:
        from db import get_conn

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        ms = int((time.perf_counter() - t0) * 1000)
        log_db_connect_result(True, ms)
        return True
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        log_db_connect_result(False, ms, error=exc)
        return False
