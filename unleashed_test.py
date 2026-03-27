from __future__ import annotations

from datetime import datetime
import os
import uuid
from typing import Any, Dict

from unleashed_db import (
    SetupRequiredError,
    clear_connection_test_data,
    clear_endpoint_table,
    delete_test_rows,
    ensure_audit_columns,
    insert_connection_test_rows,
    log_run,
    update_endpoint_control,
)
from unleashed_jobs import run_endpoint_job


def _new_run_ref(prefix: str) -> str:
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _env_name() -> str:
    return os.getenv("APP_ENV", "local")


def run_connection_test(triggered_by: str = "ui") -> Dict[str, Any]:
    started = datetime.utcnow()
    run_ref = _new_run_ref("CONN_TEST")
    try:
        result = insert_connection_test_rows()
        status = "PASS"
        message = "Database connection successful. 10 test rows written."
        error_message = None
    except SetupRequiredError as exc:
        result = {"rows_written": 0}
        status = "FAIL"
        message = "Database setup missing."
        error_message = str(exc)
    except Exception as exc:
        result = {"rows_written": 0}
        status = "FAIL"
        message = "Database connection test failed."
        error_message = str(exc)

    finished = datetime.utcnow()
    log_run(
        {
            "RunRef": run_ref,
            "EndpointName": "ConnectionTest",
            "RunType": "TEST",
            "RunMode": "connection_test",
            "Status": status,
            "StartedAt": started,
            "FinishedAt": finished,
            "DurationSeconds": int((finished - started).total_seconds()),
            "RowsWritten": result.get("rows_written", 0),
            "Message": message,
            "ErrorMessage": error_message,
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )
    return {
        "status": status,
        "message": message if status == "PASS" else f"{message} Error: {error_message}",
        "rows_written": result.get("rows_written", 0),
        "run_ref": run_ref,
    }


def clear_connection_test(triggered_by: str = "ui") -> Dict[str, Any]:
    started = datetime.utcnow()
    run_ref = _new_run_ref("CONN_CLEAR")
    deleted = clear_connection_test_data()
    finished = datetime.utcnow()
    log_run(
        {
            "RunRef": run_ref,
            "EndpointName": "ConnectionTest",
            "RunType": "TEST",
            "RunMode": "clear_connection_test_data",
            "Status": "PASS",
            "StartedAt": started,
            "FinishedAt": finished,
            "DurationSeconds": int((finished - started).total_seconds()),
            "RowsDeleted": deleted,
            "Message": "Connection test data cleared.",
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )
    return {"status": "PASS", "rows_deleted": deleted, "run_ref": run_ref}


def run_sample_db_test(endpoint_name: str, triggered_by: str = "ui") -> Dict[str, Any]:
    ensure_audit_columns(endpoint_name)
    delete_test_rows(endpoint_name)
    run_ref = _new_run_ref("SAMPLE")
    started = datetime.utcnow()
    try:
        result = run_endpoint_job(
            mode="sample_test",
            endpoint_name=endpoint_name,
            run_type="TEST",
            run_ref=run_ref,
            max_records=10,
            start_after=None,
        )
        status = "PASS"
        error_message = None
        message = "Sample DB test succeeded."
    except Exception as exc:
        result = {"rows_fetched": 0, "rows_written": 0, "checkpoint_end": None}
        status = "FAIL"
        error_message = str(exc)
        message = "Sample DB test failed."

    finished = datetime.utcnow()
    log_run(
        {
            "RunRef": run_ref,
            "EndpointName": endpoint_name,
            "RunType": "TEST",
            "RunMode": "sample_test",
            "Status": status,
            "StartedAt": started,
            "FinishedAt": finished,
            "DurationSeconds": int((finished - started).total_seconds()),
            "RowsFetched": result["rows_fetched"],
            "RowsWritten": result["rows_written"],
            "CheckpointStart": None,
            "CheckpointEnd": result.get("checkpoint_end"),
            "TargetTable": f"unleashed.{endpoint_name}",
            "Message": message,
            "ErrorMessage": error_message,
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )
    update_endpoint_control(
        endpoint_name,
        {
            "LastTestRunRef": run_ref,
            "LastTestRunAt": finished,
            "LastCheckpoint": result.get("checkpoint_end"),
            "LastRowCount": result["rows_written"],
            "LastStatus": status,
            "NextAction": "Review sample run result",
        },
    )
    return {
        "status": status,
        "records_processed": result["rows_fetched"],
        "rows_written": result["rows_written"],
        "run_ref": run_ref,
        "error": error_message,
    }


def clear_test_rows(endpoint_name: str, triggered_by: str = "ui") -> Dict[str, Any]:
    run_ref = _new_run_ref("CLEAR_TEST")
    started = datetime.utcnow()
    deleted = delete_test_rows(endpoint_name)
    finished = datetime.utcnow()
    log_run(
        {
            "RunRef": run_ref,
            "EndpointName": endpoint_name,
            "RunType": "TEST",
            "RunMode": "clear_test_rows",
            "Status": "PASS",
            "StartedAt": started,
            "FinishedAt": finished,
            "DurationSeconds": int((finished - started).total_seconds()),
            "RowsDeleted": deleted,
            "TargetTable": f"unleashed.{endpoint_name}",
            "Message": "Cleared endpoint TEST rows.",
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )
    return {"status": "PASS", "rows_deleted": deleted, "run_ref": run_ref}


def clear_endpoint_for_production_reset(endpoint_name: str, triggered_by: str = "ui") -> Dict[str, Any]:
    run_ref = _new_run_ref("CLEAR_ENDPOINT")
    started = datetime.utcnow()
    deleted = clear_endpoint_table(endpoint_name)
    finished = datetime.utcnow()
    log_run(
        {
            "RunRef": run_ref,
            "EndpointName": endpoint_name,
            "RunType": "FULL",
            "RunMode": "clear_endpoint",
            "Status": "PASS",
            "StartedAt": started,
            "FinishedAt": finished,
            "DurationSeconds": int((finished - started).total_seconds()),
            "RowsDeleted": deleted,
            "TargetTable": f"unleashed.{endpoint_name}",
            "Message": "Endpoint table cleared for production reset.",
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )
    update_endpoint_control(
        endpoint_name,
        {
            "LastStatus": "RESET",
            "NextAction": "Run full load",
            "LastRowCount": 0,
        },
    )
    return {"status": "PASS", "rows_deleted": deleted, "run_ref": run_ref}
