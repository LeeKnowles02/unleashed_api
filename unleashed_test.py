from __future__ import annotations

from datetime import datetime
import os
import uuid
from typing import Any, Dict, List, Tuple

from unleashed_db import (
    SetupRequiredError,
    clear_connection_test_data,
    clear_endpoint_table,
    delete_test_rows,
    ensure_audit_columns,
    fetch_rows_by_runref,
    insert_connection_test_rows,
    log_assessment,
    log_run,
    update_endpoint_control,
)
from unleashed_jobs import run_endpoint_job
from unleashed_test_assess import assess_incremental_validation


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


def run_incremental_validation_test(endpoint_name: str, triggered_by: str = "ui") -> Dict[str, Any]:
    if endpoint_name != "SalesOrders":
        raise ValueError("Incremental validation is currently supported for SalesOrders only.")

    ensure_audit_columns(endpoint_name)
    parent_run_ref = _new_run_ref("INC_PARENT")

    # Control run: first 20
    delete_test_rows(endpoint_name)
    control_ref = _new_run_ref("INC_CTRL")
    control = run_endpoint_job(
        mode="incremental_control",
        endpoint_name=endpoint_name,
        run_type="TEST",
        run_ref=control_ref,
        max_records=20,
    )
    log_run(
        {
            "RunRef": control_ref,
            "ParentRunRef": parent_run_ref,
            "EndpointName": endpoint_name,
            "RunType": "TEST",
            "RunMode": "incremental_control",
            "Status": control["status"],
            "StartedAt": control["started_at"],
            "FinishedAt": control["finished_at"],
            "DurationSeconds": int((control["finished_at"] - control["started_at"]).total_seconds()),
            "RowsFetched": control["rows_fetched"],
            "RowsWritten": control["rows_written"],
            "CheckpointStart": control.get("checkpoint_start"),
            "CheckpointEnd": control.get("checkpoint_end"),
            "TargetTable": f"unleashed.{endpoint_name}",
            "Message": "Incremental validation control run",
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )

    delete_test_rows(endpoint_name)

    # Batch 1: first 10
    batch1_ref = _new_run_ref("INC_B1")
    batch1 = run_endpoint_job(
        mode="incremental_batch",
        endpoint_name=endpoint_name,
        run_type="TEST",
        run_ref=batch1_ref,
        max_records=10,
    )
    log_run(
        {
            "RunRef": batch1_ref,
            "ParentRunRef": parent_run_ref,
            "EndpointName": endpoint_name,
            "RunType": "TEST",
            "RunMode": "incremental_batch_1",
            "Status": batch1["status"],
            "StartedAt": batch1["started_at"],
            "FinishedAt": batch1["finished_at"],
            "DurationSeconds": int((batch1["finished_at"] - batch1["started_at"]).total_seconds()),
            "RowsFetched": batch1["rows_fetched"],
            "RowsWritten": batch1["rows_written"],
            "CheckpointStart": batch1.get("checkpoint_start"),
            "CheckpointEnd": batch1.get("checkpoint_end"),
            "TargetTable": f"unleashed.{endpoint_name}",
            "Message": "Incremental validation batch 1",
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )

    # Batch 2: next 10 after checkpoint
    batch2_ref = _new_run_ref("INC_B2")
    batch2 = run_endpoint_job(
        mode="incremental_batch",
        endpoint_name=endpoint_name,
        run_type="TEST",
        run_ref=batch2_ref,
        max_records=10,
        start_after=batch1.get("checkpoint_end"),
    )
    log_run(
        {
            "RunRef": batch2_ref,
            "ParentRunRef": parent_run_ref,
            "EndpointName": endpoint_name,
            "RunType": "TEST",
            "RunMode": "incremental_batch_2",
            "Status": batch2["status"],
            "StartedAt": batch2["started_at"],
            "FinishedAt": batch2["finished_at"],
            "DurationSeconds": int((batch2["finished_at"] - batch2["started_at"]).total_seconds()),
            "RowsFetched": batch2["rows_fetched"],
            "RowsWritten": batch2["rows_written"],
            "CheckpointStart": batch2.get("checkpoint_start"),
            "CheckpointEnd": batch2.get("checkpoint_end"),
            "TargetTable": f"unleashed.{endpoint_name}",
            "Message": "Incremental validation batch 2",
            "TriggerSource": "ui_button",
            "TriggeredBy": triggered_by,
            "Environment": _env_name(),
        }
    )

    control_keys = fetch_rows_by_runref(endpoint_name, control_ref)
    batch1_keys = fetch_rows_by_runref(endpoint_name, batch1_ref)
    batch2_keys = fetch_rows_by_runref(endpoint_name, batch2_ref)

    required_fields_ok = len([k for k in (batch1_keys + batch2_keys) if k[0] and k[1]])
    assessment = assess_incremental_validation(
        control_keys=control_keys,
        batch1_keys=batch1_keys,
        batch2_keys=batch2_keys,
        control_rows=control["rows_written"],
        incremental_rows=batch1["rows_written"] + batch2["rows_written"],
        required_fields_ok=required_fields_ok,
        checkpoint_progressed=bool(batch1.get("checkpoint_end") and batch2.get("checkpoint_end")),
    )
    assessment_ref = _new_run_ref("ASSESS")

    log_assessment(
        {
            "AssessmentRef": assessment_ref,
            "ParentRunRef": parent_run_ref,
            "EndpointName": endpoint_name,
            "ControlRunRef": control_ref,
            "Batch1RunRef": batch1_ref,
            "Batch2RunRef": batch2_ref,
            "AssessmentType": "incremental_20_vs_10_plus_10",
            "ControlUnits": 20,
            "IncrementalUnits": 20,
            **assessment,
            "AssessedBy": triggered_by,
        }
    )

    update_endpoint_control(
        endpoint_name,
        {
            "LastAssessmentRef": assessment_ref,
            "LastAssessmentStatus": assessment["OverallAssessment"],
            "LastSignOffStatus": assessment["SignOffStatus"],
            "LastTestRunRef": batch2_ref,
            "LastTestRunAt": datetime.utcnow(),
            "LastCheckpoint": batch2.get("checkpoint_end"),
            "LastRowCount": batch1["rows_written"] + batch2["rows_written"],
            "LastStatus": assessment["OverallAssessment"],
            "NextAction": "Proceed to full run" if assessment["SignOffStatus"] == "READY_FOR_PRODUCTION" else "Investigate test failures",
            "Notes": assessment["Notes"],
        },
    )

    return {
        "status": assessment["OverallAssessment"],
        "sign_off_status": assessment["SignOffStatus"],
        "records_processed": control["rows_fetched"] + batch1["rows_fetched"] + batch2["rows_fetched"],
        "rows_written": control["rows_written"] + batch1["rows_written"] + batch2["rows_written"],
        "summary": assessment["Notes"],
        "run_ref_control": control_ref,
        "run_ref_a": batch1_ref,
        "run_ref_b": batch2_ref,
        "assessment_ref": assessment_ref,
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
