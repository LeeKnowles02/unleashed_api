from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple

from db import get_conn


class SetupRequiredError(RuntimeError):
    """Raised when DB setup objects are missing."""


AUDIT_COLUMNS = ("RunType", "RunRef", "LoadedAt", "EndpointName")

ENDPOINT_TABLES = {
    "Customers": "unleashed.Customers",
    "Invoices": "unleashed.Invoices",
    "Products": "unleashed.Products",
    "Warehouses": "unleashed.Warehouses",
    "StockOnHand": "unleashed.StockOnHand",
    "CreditNotes": "unleashed.CreditNotes",
    "SalesShipments": "unleashed.SalesShipments",
    "SalesOrders": "unleashed.SalesOrders",
    "Suppliers": "unleashed.Suppliers",
}


def _quote(name: str) -> str:
    return f"[{name}]"


def _table_from_endpoint(endpoint_name: str) -> str:
    if endpoint_name not in ENDPOINT_TABLES:
        raise ValueError(f"Unsupported endpoint: {endpoint_name}")
    return ENDPOINT_TABLES[endpoint_name]


def _fetch_primary_keys(cursor, schema_name: str, table_name: str) -> List[str]:
    cursor.execute(
        """
        SELECT c.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE c
          ON c.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
         AND c.TABLE_SCHEMA = tc.TABLE_SCHEMA
         AND c.TABLE_NAME = tc.TABLE_NAME
        WHERE tc.TABLE_SCHEMA = ?
          AND tc.TABLE_NAME = ?
          AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        ORDER BY c.ORDINAL_POSITION
        """,
        schema_name,
        table_name,
    )
    return [r[0] for r in cursor.fetchall()]


def _split_table_name(qualified_name: str) -> Tuple[str, str]:
    schema_name, table_name = qualified_name.split(".", 1)
    return schema_name, table_name


def _assert_table_exists(cursor, qualified_table_name: str) -> None:
    cursor.execute("SELECT OBJECT_ID(?, 'U')", qualified_table_name)
    if cursor.fetchone()[0] is None:
        raise SetupRequiredError(
            f"Missing DB table: {qualified_table_name}. "
            "Run the schema setup SQL with an admin account, then retry."
        )


def _assert_columns_exist(cursor, qualified_table_name: str, required_columns: Sequence[str]) -> None:
    missing: List[str] = []
    for col in required_columns:
        cursor.execute("SELECT COL_LENGTH(?, ?)", qualified_table_name, col)
        if cursor.fetchone()[0] is None:
            missing.append(col)
    if missing:
        raise SetupRequiredError(
            f"Missing required columns on {qualified_table_name}: {', '.join(missing)}. "
            "As dbo/admin: run unleashed_schema/patch_audit_columns_endpoint_tables.sql. "
            "Or grant ALTER on schema unleashed to the app user (see "
            "unleashed_schema/grant_alter_unleashed_to_app_user.sql), then run "
            "python scripts/apply_audit_columns.py."
        )


def ensure_audit_columns(endpoint_name: str) -> None:
    full_table_name = _table_from_endpoint(endpoint_name)
    with get_conn() as conn:
        cur = conn.cursor()
        _assert_table_exists(cur, full_table_name)
        _assert_columns_exist(cur, full_table_name, AUDIT_COLUMNS)


def ensure_control_tables() -> None:
    required_tables = (
        "unleashed.ConnectionTest",
        "unleashed.RunLog",
        "unleashed.TestAssessmentLog",
        "unleashed.EndpointControl",
    )
    with get_conn() as conn:
        cur = conn.cursor()
        for table_name in required_tables:
            _assert_table_exists(cur, table_name)


def insert_connection_test_rows() -> Dict[str, Any]:
    ensure_control_tables()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM unleashed.ConnectionTest")
        now_utc = datetime.utcnow()
        rows_to_insert = [(i, f"TEST_ROW_{i}", now_utc) for i in range(1, 11)]
        cur.executemany(
            """
            INSERT INTO unleashed.ConnectionTest ([ID], [TestValue], [CreatedAt])
            VALUES (?, ?, ?)
            """,
            rows_to_insert,
        )
        conn.commit()
    return {"status": "SUCCESS", "rows_written": 10}


def clear_connection_test_data() -> int:
    ensure_control_tables()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM unleashed.ConnectionTest")
        deleted = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        conn.commit()
    return deleted


def delete_test_rows(endpoint_name: str) -> int:
    table_name = _table_from_endpoint(endpoint_name)
    ensure_audit_columns(endpoint_name)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table_name} WHERE [RunType] = 'TEST'")
        deleted = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        conn.commit()
    return deleted


def clear_endpoint_table(endpoint_name: str) -> int:
    table_name = _table_from_endpoint(endpoint_name)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table_name}")
        deleted = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        conn.commit()
    return deleted


def write_endpoint_rows(
    *,
    endpoint_name: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    run_type: str,
    run_ref: str,
) -> Dict[str, int]:
    table_name = _table_from_endpoint(endpoint_name)
    schema_name, base_table = _split_table_name(table_name)
    ensure_audit_columns(endpoint_name)
    if not rows:
        try:
            from integration_log_writer import log_info

            log_info(
                f"Table upsert skipped for endpoint '{endpoint_name}': zero rows to write (target {table_name}); MERGE not executed.",
                integration_name="azure_sql",
                module_name="unleashed_db",
                function_name="write_endpoint_rows",
                event_type="table_upsert_skipped",
                action="merge_upsert",
                entity_name=table_name,
                endpoint=endpoint_name,
                status="SKIPPED",
                detail="Transformation returned no rows; check API filters, pagination, and Unleashed data.",
            )
        except Exception:
            pass
        return {"rows_written": 0}

    t0 = time.perf_counter()
    try:
        from integration_log_writer import log_error, log_info

        log_info(
            f"Table MERGE upsert starting: target={table_name}, endpoint_name={endpoint_name!r}, run_type={run_type!r}, "
            f"run_ref={run_ref!r}, batch_row_count={len(rows)}, source_column_count={len(headers)} "
            f"(plus audit columns RunType, RunRef, LoadedAt, EndpointName).",
            integration_name="azure_sql",
            module_name="unleashed_db",
            function_name="write_endpoint_rows",
            event_type="table_upsert_started",
            action="merge_upsert",
            step_name="temp_table_and_merge",
            entity_name=table_name,
            endpoint=endpoint_name,
            status="STARTED",
            record_count=len(rows),
            detail="Pattern: load #temp from values, MERGE ON primary key, UPDATE non-PK columns, INSERT new keys.",
        )
    except Exception:
        pass

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            pk_columns = _fetch_primary_keys(cur, schema_name, base_table)
            if not pk_columns:
                raise RuntimeError(f"No primary key found for {table_name}")

            try:
                from integration_log_writer import log_info

                log_info(
                    f"Resolved primary key for MERGE: table={table_name}, pk_columns={pk_columns}.",
                    integration_name="azure_sql",
                    module_name="unleashed_db",
                    function_name="write_endpoint_rows",
                    event_type="table_upsert_progress",
                    action="merge_upsert",
                    step_name="pk_resolved",
                    entity_name=table_name,
                    endpoint=endpoint_name,
                    status="IN_PROGRESS",
                )
            except Exception:
                pass

            loaded_at = datetime.utcnow()
            final_columns = list(headers) + ["RunType", "RunRef", "LoadedAt", "EndpointName"]

            values: List[Tuple[Any, ...]] = []
            for row in rows:
                values.append(tuple(row) + (run_type, run_ref, loaded_at, endpoint_name))

            temp_table = "#tmp_unleashed_write"
            cur.execute(
                f"""
                SELECT TOP 0 {', '.join(_quote(c) for c in final_columns)}
                INTO {temp_table}
                FROM {table_name}
                """
            )

            placeholders = ", ".join(["?"] * len(final_columns))
            t_bulk = time.perf_counter()
            cur.executemany(
                f"""
                INSERT INTO {temp_table} ({', '.join(_quote(c) for c in final_columns)})
                VALUES ({placeholders})
                """,
                values,
            )
            bulk_ms = int((time.perf_counter() - t_bulk) * 1000)
            try:
                from integration_log_writer import log_info

                log_info(
                    f"Staging complete: inserted {len(values)} row(s) into session temp table {temp_table} in {bulk_ms} ms.",
                    integration_name="azure_sql",
                    module_name="unleashed_db",
                    function_name="write_endpoint_rows",
                    event_type="table_bulk_insert_staging_completed",
                    action="insert_temp",
                    step_name=temp_table,
                    entity_name=table_name,
                    endpoint=endpoint_name,
                    status="SUCCESS",
                    record_count=len(values),
                    duration_ms=bulk_ms,
                )
            except Exception:
                pass

            on_clause = " AND ".join([f"target.{_quote(c)} = src.{_quote(c)}" for c in pk_columns])
            update_columns = [c for c in final_columns if c not in pk_columns]
            update_set = ", ".join([f"target.{_quote(c)} = src.{_quote(c)}" for c in update_columns])
            insert_cols = ", ".join(_quote(c) for c in final_columns)
            insert_values = ", ".join([f"src.{_quote(c)}" for c in final_columns])

            t_merge = time.perf_counter()
            cur.execute(
                f"""
                MERGE {table_name} AS target
                USING {temp_table} AS src
                ON {on_clause}
                WHEN MATCHED THEN
                  UPDATE SET {update_set}
                WHEN NOT MATCHED BY TARGET THEN
                  INSERT ({insert_cols})
                  VALUES ({insert_values});
                """
            )
            merge_ms = int((time.perf_counter() - t_merge) * 1000)
            conn.commit()
    except Exception as exc:
        total_ms = int((time.perf_counter() - t0) * 1000)
        try:
            from integration_log_writer import log_error

            log_error(
                f"Table MERGE upsert failed after {total_ms} ms: target={table_name}, endpoint={endpoint_name!r}, "
                f"run_ref={run_ref!r}, attempted_batch_rows={len(rows)}.",
                exc=exc,
                integration_name="azure_sql",
                module_name="unleashed_db",
                function_name="write_endpoint_rows",
                event_type="table_upsert_failed",
                action="merge_upsert",
                entity_name=table_name,
                endpoint=endpoint_name,
                status="FAIL",
                duration_ms=total_ms,
                record_count=len(rows),
                detail="Transaction rolled back. Check PK mismatch, missing columns, data types, and unleashed schema. "
                "Re-run after fixing dbo/unleashed DDL or row shape.",
            )
        except Exception:
            pass
        raise

    total_ms = int((time.perf_counter() - t0) * 1000)
    try:
        from integration_log_writer import log_info

        log_info(
            f"Table MERGE upsert completed: target={table_name}, committed batch of {len(rows)} source row(s) in {total_ms} ms "
            f"(MERGE timing includes match/insert/update; per-operation insert/update counts require OUTPUT clause — not captured here).",
            integration_name="azure_sql",
            module_name="unleashed_db",
            function_name="write_endpoint_rows",
            event_type="table_upsert_completed",
            action="merge_upsert",
            entity_name=table_name,
            endpoint=endpoint_name,
            status="SUCCESS",
            record_count=len(rows),
            duration_ms=total_ms,
            detail="RowsWritten in RunLog equals batch size; for exact INSERT vs UPDATE split, extend MERGE with OUTPUT.",
        )
    except Exception:
        pass

    return {"rows_written": len(rows)}


def log_run(payload: Dict[str, Any]) -> None:
    try:
        ensure_control_tables()
        columns = list(payload.keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"""
            INSERT INTO unleashed.RunLog ({', '.join(_quote(c) for c in columns)})
            VALUES ({placeholders})
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, *[payload[c] for c in columns])
            conn.commit()
    except Exception:
        # Logging must never break the main workflow.
        return


def log_assessment(payload: Dict[str, Any]) -> None:
    try:
        ensure_control_tables()
        columns = list(payload.keys())
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"""
            INSERT INTO unleashed.TestAssessmentLog ({', '.join(_quote(c) for c in columns)})
            VALUES ({placeholders})
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, *[payload[c] for c in columns])
            conn.commit()
    except Exception:
        return


def update_endpoint_control(endpoint_name: str, updates: Dict[str, Any]) -> None:
    try:
        ensure_control_tables()
        now_utc = datetime.utcnow()
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(1) FROM unleashed.EndpointControl WHERE [EndpointName] = ?",
                endpoint_name,
            )
            exists = cur.fetchone()[0] > 0
            if not exists:
                cur.execute(
                    """
                    INSERT INTO unleashed.EndpointControl ([EndpointName], [UpdatedAt])
                    VALUES (?, ?)
                    """,
                    endpoint_name,
                    now_utc,
                )

            if updates:
                set_clause = ", ".join([f"{_quote(k)} = ?" for k in updates.keys()])
                values = list(updates.values()) + [now_utc, endpoint_name]
                cur.execute(
                    f"""
                    UPDATE unleashed.EndpointControl
                    SET {set_clause}, [UpdatedAt] = ?
                    WHERE [EndpointName] = ?
                    """,
                    *values,
                )
            conn.commit()
    except Exception:
        return
