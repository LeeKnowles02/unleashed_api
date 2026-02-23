import os
import json
import uuid
import hashlib
from typing import Any, Optional
from dotenv import load_dotenv
import pyodbc

load_dotenv()

SERVER = os.environ["AZURE_SQL_SERVER"]
DB = os.environ["AZURE_SQL_DB"]
USER = os.environ["AZURE_SQL_USER"]
PWD = os.environ["AZURE_SQL_PASSWORD"]

CONN_STR = (
    "Driver={ODBC Driver 18 for SQL Server};"
    f"Server=tcp:{SERVER},1433;"
    f"Database={DB};"
    f"Uid={USER};"
    f"Pwd={PWD};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

def _sha256_bytes(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()

def get_conn() -> pyodbc.Connection:
    return pyodbc.connect(CONN_STR)

def start_run(company_id: Optional[str] = None) -> str:
    run_id = str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dbo.etl_run (run_id, company_id, status) VALUES (?, ?, ?)",
            run_id, company_id, "RUNNING"
        )
        conn.commit()
    return run_id

def finish_run(run_id: str, status: str, notes: Optional[str] = None) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE dbo.etl_run
            SET finished_at_utc = SYSUTCDATETIME(),
                status = ?,
                notes = ?
            WHERE run_id = ?
        """, status, notes, run_id)
        conn.commit()

def insert_raw_payload(
    run_id: str,
    company_id: Optional[str],
    endpoint: str,
    http_status: Optional[int],
    payload_obj: Any,
    request_url: Optional[str] = None,
    page_number: Optional[int] = None,
    api_cursor: Optional[str] = None,
) -> None:
    payload_json = json.dumps(payload_obj, ensure_ascii=False)
    payload_hash = _sha256_bytes(payload_json)

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO raw.api_payload
              (run_id, company_id, endpoint, http_status, page_number, api_cursor, request_url, payload_json, payload_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, run_id, company_id, endpoint, http_status, page_number, api_cursor, request_url, payload_json, payload_hash)
        conn.commit()


