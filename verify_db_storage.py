"""
Verify that ETL run and raw API payload data is stored correctly in Azure SQL.
Run: python verify_db_storage.py

Checks:
  - Connection to Azure SQL
  - dbo.etl_run: run metadata (start/finish, status)
  - raw.api_payload: raw JSON from every export (Products, SalesOrders, Invoices, etc.)
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    required = ["AZURE_SQL_SERVER", "AZURE_SQL_DB", "AZURE_SQL_USER", "AZURE_SQL_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print("Missing env vars:", ", ".join(missing))
        print("Set them in .env and run again.")
        sys.exit(1)

    try:
        from db import get_conn
    except Exception as e:
        print("Failed to import db:", e)
        sys.exit(1)

    print("Connecting to Azure SQL...")
    try:
        with get_conn() as conn:
            cur = conn.cursor()

            # 1) dbo.etl_run
            try:
                cur.execute("SELECT COUNT(*) FROM dbo.etl_run")
                run_count = cur.fetchone()[0]
                print(f"\ndbo.etl_run: {run_count} row(s)")
            except Exception as e:
                print(f"\ndbo.etl_run: ERROR - {e}")
                print("  (Table may not exist. Create it with run_id, company_id, status, finished_at_utc, notes.)")
                run_count = None

            if run_count and run_count > 0:
                cur.execute("""
                    SELECT TOP 5 run_id, company_id, status, finished_at_utc
                    FROM dbo.etl_run
                    ORDER BY run_id DESC
                """)
                rows = cur.fetchall()
                print("  Latest runs:")
                for r in rows:
                    print(f"    {r[0][:8]}... | {r[1]} | {r[2]} | {r[3]}")

            # 2) raw.api_payload
            try:
                cur.execute("SELECT COUNT(*) FROM raw.api_payload")
                payload_count = cur.fetchone()[0]
                print(f"\nraw.api_payload: {payload_count} row(s)")
            except Exception as e:
                print(f"\nraw.api_payload: ERROR - {e}")
                print("  (Schema 'raw' and table 'api_payload' may not exist.)")
                payload_count = None

            if payload_count and payload_count > 0:
                cur.execute("""
                    SELECT endpoint, COUNT(*) AS cnt
                    FROM raw.api_payload
                    GROUP BY endpoint
                    ORDER BY endpoint
                """)
                rows = cur.fetchall()
                print("  Stored data by endpoint (whole table per run):")
                for r in rows:
                    print(f"    {r[0]}: {r[1]} row(s)")
                cur.execute("""
                    SELECT TOP 5 payload_id, run_id, endpoint, http_status, extracted_at_utc
                    FROM raw.api_payload
                    ORDER BY payload_id DESC
                """)
                rows = cur.fetchall()
                print("  Latest payloads:")
                for r in rows:
                    run_short = (r[1] or "")[:8] + "..." if r[1] else "NULL"
                    print(f"    id={r[0]} | run={run_short} | endpoint={r[2]} | status={r[3]} | at={r[4]}")

            print("\n--- How to view the data ---")
            print("  In SSMS / Azure Data Studio, run:")
            print("  -- List all stored payloads (metadata):")
            print("  SELECT payload_id, run_id, endpoint, http_status, extracted_at_utc FROM raw.api_payload ORDER BY payload_id DESC;")
            print("  -- View full JSON for one endpoint (e.g. SalesOrders):")
            print("  SELECT payload_json FROM raw.api_payload WHERE endpoint = 'SalesOrders' ORDER BY payload_id DESC;")
            print("  -- Parse JSON into rows (Azure SQL / SQL Server 2016+):")
            print("  SELECT p.payload_id, p.endpoint, j.* FROM raw.api_payload p CROSS APPLY OPENJSON(p.payload_json, '$.Items') j WHERE p.endpoint = 'SalesOrders';")
            print("\n--- Done. ---")

    except Exception as e:
        print("Connection or query failed:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
