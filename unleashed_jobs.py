from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from exports import sales_orders
from unleashed_client import UnleashedClient
from unleashed_db import write_endpoint_rows


cfg = Config()
client = UnleashedClient(
    base_url=cfg.UNLEASHED_BASE_URL,
    api_id=cfg.UNLEASHED_API_ID,
    api_key=cfg.UNLEASHED_API_KEY,
    client_type=cfg.UNLEASHED_CLIENT_TYPE,
    timeout_seconds=cfg.REQUEST_TIMEOUT_SECONDS,
)


def _row_key_sales_orders(row: List[Any], header_index: Dict[str, int]) -> str:
    return f"{row[header_index['OrderGuid']]}|{row[header_index['LineNumber']]}"


def _fetch_sales_orders_rows(
    *,
    max_records: Optional[int] = None,
    start_after: Optional[str] = None,
) -> Tuple[List[str], List[List[Any]], Optional[str]]:
    _, headers, rows = sales_orders.from_api(client)
    idx = {h: i for i, h in enumerate(headers)}
    rows_sorted = sorted(rows, key=lambda r: _row_key_sales_orders(r, idx))

    if start_after:
        rows_sorted = [r for r in rows_sorted if _row_key_sales_orders(r, idx) > start_after]

    if max_records is not None:
        rows_sorted = rows_sorted[:max_records]

    checkpoint_end = _row_key_sales_orders(rows_sorted[-1], idx) if rows_sorted else None
    return headers, rows_sorted, checkpoint_end


def run_endpoint_job(
    *,
    mode: str,
    endpoint_name: str,
    run_type: str,
    run_ref: str,
    max_records: Optional[int] = None,
    start_after: Optional[str] = None,
) -> Dict[str, Any]:
    if endpoint_name != "SalesOrders":
        raise ValueError(f"Unsupported endpoint: {endpoint_name}")

    started_at = datetime.utcnow()
    if mode not in {"full", "sample_test"}:
        raise ValueError(f"Unsupported mode: {mode}")

    headers, rows, checkpoint_end = _fetch_sales_orders_rows(
        max_records=max_records,
        start_after=start_after,
    )
    write_result = write_endpoint_rows(
        endpoint_name=endpoint_name,
        headers=headers,
        rows=rows,
        run_type=run_type,
        run_ref=run_ref,
    )

    return {
        "status": "PASS",
        "mode": mode,
        "endpoint_name": endpoint_name,
        "run_type": run_type,
        "run_ref": run_ref,
        "started_at": started_at,
        "finished_at": datetime.utcnow(),
        "rows_fetched": len(rows),
        "rows_written": write_result["rows_written"],
        "checkpoint_start": start_after,
        "checkpoint_end": checkpoint_end,
    }
