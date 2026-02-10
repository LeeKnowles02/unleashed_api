import os
import json
import uuid
import hashlib
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

def sha256_bytes(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()

def main():
    print("Starting DB test...")
    with pyodbc.connect(CONN_STR) as conn:
        cur = conn.cursor()

        # 1) create a run
        run_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO dbo.etl_run (run_id, company_id, status) VALUES (?, ?, ?)",
            run_id, "dev_company", "RUNNING"
        )

        # 2) insert one raw payload row
        payload_obj = {"hello": "world", "items": [1, 2, 3]}
        payload_json = json.dumps(payload_obj, ensure_ascii=False)
        payload_hash = sha256_bytes(payload_json)

        cur.execute("""
            INSERT INTO raw.api_payload
              (run_id, company_id, endpoint, http_status, page_number, api_cursor, request_url, payload_json, payload_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        run_id, "dev_company", "TEST_ENDPOINT", 200, 1, None,
        "https://example.com/test", payload_json, payload_hash)

        # 3) mark run finished
        cur.execute("""
            UPDATE dbo.etl_run
            SET finished_at_utc = SYSUTCDATETIME(), status = ?
            WHERE run_id = ?
        """, "SUCCESS", run_id)

        conn.commit()

        # 4) read back to prove it worked
        cur.execute("""
            SELECT TOP 1 payload_id, endpoint, extracted_at_utc
            FROM raw.api_payload
            ORDER BY payload_id DESC
        """)
        print("Latest payload row:", cur.fetchone())

if __name__ == "__main__":
    main()
