from __future__ import annotations

import json
import traceback
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from config import Config
from db import get_conn


PROCESS_NAME = "Unleashed Exchange Rates Load"
SOURCE_SYSTEM = "Frankfurter"


def _safe_config_snapshot(cfg: Config) -> Dict[str, str]:
    return {
        "FRANKFURTER_BASE_URL": cfg.FRANKFURTER_BASE_URL,
        "FRANKFURTER_BASE": cfg.FRANKFURTER_BASE,
        "FRANKFURTER_QUOTES": cfg.FRANKFURTER_QUOTES,
        "FRANKFURTER_PROVIDER": cfg.FRANKFURTER_PROVIDER,
    }


def _build_quotes_list(quotes_raw: str) -> List[str]:
    return [q.strip().upper() for q in (quotes_raw or "").split(",") if q.strip()]


def log_process_start(action_name: str, detail: Optional[str] = None) -> Optional[int]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO unleashed.ProcessLog (ProcessName, ActionName, Status, Detail)
            VALUES (?, ?, ?, ?)
            """,
            PROCESS_NAME,
            action_name,
            "STARTED",
            detail,
        )
        cur.execute("SELECT CAST(SCOPE_IDENTITY() AS BIGINT)")
        row = cur.fetchone()
        conn.commit()
        return int(row[0]) if row and row[0] is not None else None


def log_process_success(log_id: Optional[int], action_name: str, detail: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        if log_id is not None:
            cur.execute(
                """
                UPDATE unleashed.ProcessLog
                SET Status = ?, Detail = ?, FinishedAtUTC = SYSUTCDATETIME(), ErrorMessage = NULL
                WHERE LogID = ?
                """,
                "SUCCESS",
                detail,
                log_id,
            )
        else:
            cur.execute(
                """
                INSERT INTO unleashed.ProcessLog (ProcessName, ActionName, Status, Detail, FinishedAtUTC)
                VALUES (?, ?, ?, ?, SYSUTCDATETIME())
                """,
                PROCESS_NAME,
                action_name,
                "SUCCESS",
                detail,
            )
        conn.commit()


def log_process_failure(log_id: Optional[int], action_name: str, detail: str, error_message: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        if log_id is not None:
            cur.execute(
                """
                UPDATE unleashed.ProcessLog
                SET Status = ?, Detail = ?, ErrorMessage = ?, FinishedAtUTC = SYSUTCDATETIME()
                WHERE LogID = ?
                """,
                "FAILED",
                detail,
                error_message,
                log_id,
            )
        else:
            cur.execute(
                """
                INSERT INTO unleashed.ProcessLog (ProcessName, ActionName, Status, Detail, ErrorMessage, FinishedAtUTC)
                VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME())
                """,
                PROCESS_NAME,
                action_name,
                "FAILED",
                detail,
                error_message,
            )
        conn.commit()


def fetch_latest_exchange_rates() -> Dict[str, Any]:
    cfg = Config()
    quotes = _build_quotes_list(cfg.FRANKFURTER_QUOTES)
    params = {
        "base": cfg.FRANKFURTER_BASE,
        "quotes": ",".join(quotes),
        "providers": cfg.FRANKFURTER_PROVIDER,
    }
    api_url = f"{cfg.FRANKFURTER_BASE_URL}?{urlencode(params)}"
    response = requests.get(
        cfg.FRANKFURTER_BASE_URL,
        params=params,
        timeout=cfg.REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    normalized: Dict[str, Any]
    # Current frankfurter.dev v2 rates response can be a list like:
    # [{"date":"YYYY-MM-DD","base":"USD","quote":"EUR","rate":0.85514}, ...]
    # Normalize that into {"date": "...", "base": "...", "rates": {"EUR": 0.85514, ...}}
    if isinstance(payload, list):
        if not payload:
            raise ValueError("Frankfurter response list is empty.")
        first = payload[0]
        if not isinstance(first, dict):
            raise ValueError("Frankfurter response list items must be JSON objects.")

        rate_date = first.get("date")
        base_currency = str(first.get("base") or "").upper().strip()
        rates: Dict[str, Any] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            quote = str(item.get("quote") or "").upper().strip()
            if quote:
                rates[quote] = item.get("rate")

        normalized = {
            "date": rate_date,
            "base": base_currency,
            "rates": rates,
        }
    elif isinstance(payload, dict):
        normalized = payload
    else:
        raise ValueError("Frankfurter response must be a JSON object or list.")

    if "date" not in normalized or "base" not in normalized or "rates" not in normalized:
        raise ValueError("Frankfurter response missing one of required fields: date, base, rates.")
    if not isinstance(normalized.get("rates"), dict) or not normalized["rates"]:
        raise ValueError("Frankfurter response 'rates' must be a non-empty object.")

    normalized["api_url"] = api_url
    normalized["provider"] = cfg.FRANKFURTER_PROVIDER
    normalized["quotes"] = quotes
    return normalized


def upsert_exchange_rates(rate_payload: Dict[str, Any]) -> int:
    rate_date = rate_payload["date"]
    base_currency = str(rate_payload["base"]).upper().strip()
    provider = str(rate_payload.get("provider") or "").strip() or None
    rates = rate_payload["rates"]

    merge_sql = """
    MERGE unleashed.ExchangeRates AS tgt
    USING (
        SELECT
            CAST(? AS DATE) AS RateDate,
            CAST(? AS CHAR(3)) AS BaseCurrency,
            CAST(? AS CHAR(3)) AS QuoteCurrency,
            CAST(? AS DECIMAL(18,8)) AS Rate,
            CAST(? AS VARCHAR(50)) AS Provider
    ) AS src
    ON tgt.RateDate = src.RateDate
    AND tgt.BaseCurrency = src.BaseCurrency
    AND tgt.QuoteCurrency = src.QuoteCurrency
    AND ISNULL(tgt.Provider, '') = ISNULL(src.Provider, '')
    WHEN MATCHED THEN
        UPDATE SET
            tgt.Rate = src.Rate,
            tgt.LoadedAtUTC = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN
        INSERT (
            RateDate,
            BaseCurrency,
            QuoteCurrency,
            Rate,
            Provider,
            SourceSystem
        )
        VALUES (
            src.RateDate,
            src.BaseCurrency,
            src.QuoteCurrency,
            src.Rate,
            src.Provider,
            'Frankfurter'
        );
    """

    rows_loaded = 0
    with get_conn() as conn:
        cur = conn.cursor()
        for quote_currency, rate_value in rates.items():
            quote = str(quote_currency).upper().strip()
            if not quote:
                continue
            try:
                normalized_rate = Decimal(str(rate_value))
            except (InvalidOperation, ValueError, TypeError):
                raise ValueError(f"Invalid rate value for {quote}: {rate_value!r}") from None
            cur.execute(
                merge_sql,
                rate_date,
                base_currency,
                quote,
                normalized_rate,
                provider,
            )
            rows_loaded += 1
        conn.commit()
    return rows_loaded


def load_latest_exchange_rates() -> Dict[str, Any]:
    action_name = "Load Latest Exchange Rates"
    cfg = Config()
    log_id: Optional[int] = None
    try:
        log_id = log_process_start(
            action_name=action_name,
            detail=f"Starting load with config: {json.dumps(_safe_config_snapshot(cfg), ensure_ascii=False)}",
        )
    except Exception:
        log_id = None

    try:
        payload = fetch_latest_exchange_rates()
        loaded_count = upsert_exchange_rates(payload)

        detail = (
            f"Loaded {loaded_count} rate(s). "
            f"rate_date={payload.get('date')}, base={payload.get('base')}, "
            f"quotes={','.join(sorted(payload.get('rates', {}).keys()))}, "
            f"provider={payload.get('provider')}, api_url={payload.get('api_url')}"
        )
        try:
            log_process_success(log_id, action_name, detail)
        except Exception:
            pass
        return {
            "status": "SUCCESS",
            "rows_loaded": loaded_count,
            "rate_date": payload.get("date"),
            "base_currency": payload.get("base"),
            "quote_currencies": sorted(payload.get("rates", {}).keys()),
            "provider": payload.get("provider"),
            "api_url": payload.get("api_url"),
        }
    except Exception as exc:
        tb = traceback.format_exc()
        failure_detail = (
            f"Exchange rate load failed. api_url_attempted={cfg.FRANKFURTER_BASE_URL}; "
            f"config={json.dumps(_safe_config_snapshot(cfg), ensure_ascii=False)}"
        )
        try:
            log_process_failure(
                log_id=log_id,
                action_name=action_name,
                detail=failure_detail,
                error_message=f"{exc}\n{tb}",
            )
        except Exception:
            pass
        raise


def get_latest_exchange_rates(limit: int = 100) -> List[Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP (?)
                RateDate,
                BaseCurrency,
                QuoteCurrency,
                Rate,
                Provider,
                LoadedAtUTC
            FROM unleashed.ExchangeRates
            ORDER BY RateDate DESC, QuoteCurrency ASC
            """,
            limit,
        )
        return cur.fetchall()


def get_latest_process_logs(limit: int = 20) -> List[Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP (?)
                LogID,
                ProcessName,
                ActionName,
                Status,
                Detail,
                ErrorMessage,
                StartedAtUTC,
                FinishedAtUTC
            FROM unleashed.ProcessLog
            WHERE ProcessName = ?
            ORDER BY LogID DESC
            """,
            limit,
            PROCESS_NAME,
        )
        return cur.fetchall()
