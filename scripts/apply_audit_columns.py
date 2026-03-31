"""
Add RunType, RunRef, LoadedAt, EndpointName to unleashed endpoint tables.

Uses the same database credentials as the app (AZURE_SQL_* in .env).
Run from repo root:

    python scripts/apply_audit_columns.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import get_conn

# Logical keys: (schema, table) — always use [schema].[table] in DDL (avoids parser issues).
TABLES = [
    ("unleashed", "Customers"),
    ("unleashed", "Invoices"),
    ("unleashed", "Products"),
    ("unleashed", "Warehouses"),
    ("unleashed", "StockOnHand"),
    ("unleashed", "CreditNotes"),
    ("unleashed", "SalesShipments"),
    ("unleashed", "SalesOrders"),
    ("unleashed", "Suppliers"),
]

COLUMNS = [
    ("RunType", "NVARCHAR(20) NULL"),
    ("RunRef", "NVARCHAR(100) NULL"),
    ("LoadedAt", "DATETIME2 NULL"),
    ("EndpointName", "NVARCHAR(100) NULL"),
]


def main() -> int:
    added = 0
    skipped = 0
    errors: list[str] = []

    with get_conn() as conn:
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT DB_NAME()")
        db_name = cur.fetchone()[0]
        print(f"Database: {db_name}")

        for schema, tbl in TABLES:
            qualified = f"{schema}.{tbl}"
            cur.execute("SELECT OBJECT_ID(?, 'U')", qualified)
            if cur.fetchone()[0] is None:
                print(f"  SKIP (no table): {qualified}")
                skipped += 1
                continue

            for col_name, col_type in COLUMNS:
                cur.execute("SELECT COL_LENGTH(?, ?)", qualified, col_name)
                length = cur.fetchone()[0]
                if length is not None:
                    continue
                ddl = f"ALTER TABLE [{schema}].[{tbl}] ADD [{col_name}] {col_type}"
                try:
                    cur.execute(ddl)
                    print(f"  OK: {table} + {col_name}")
                    added += 1
                except Exception as exc:
                    msg = f"{qualified} + {col_name}: {exc}"
                    errors.append(msg)
                    print(f"  FAIL: {msg}")

    if errors:
        print(
            "\nSome ALTERs failed. Typical cause: the app user can read/write rows but "
            "cannot ALTER tables (SQL error 1088).\n"
            "  • Run unleashed_schema/patch_audit_columns_endpoint_tables.sql as **dbo / admin**, or\n"
            "  • Run unleashed_schema/grant_alter_unleashed_to_app_user.sql (edit user name), then "
            "run this script again."
        )
        return 1
    if added == 0:
        print("\nNo new columns added (already present or tables missing).")
    else:
        print(f"\nAdded {added} column(s). Retry your export.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
