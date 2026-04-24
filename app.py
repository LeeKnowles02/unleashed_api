from dotenv import load_dotenv
from db import start_run, finish_run, start_sync_run, finish_sync_run
from schedules import add_schedule, delete_schedule, list_schedules

load_dotenv()

from flask import Flask, redirect, render_template, request, Response, flash
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import io
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, List

from config import Config
from integration_log_writer import (
    clear_integration_request_context,
    clear_run_context,
    get_correlation_id,
    log_error,
    log_info,
    log_warning,
    ping_database,
    set_correlation_id,
    set_run_context,
)
from db import get_conn
from unleashed_db import (
    ENDPOINT_TABLES,
    SetupRequiredError,
    log_run,
    update_endpoint_control,
    write_endpoint_rows,
)
from unleashed_client import UnleashedClient
from unleashed_test import (
    clear_connection_test,
    clear_endpoint_for_production_reset,
    clear_test_rows,
    run_connection_test,
    run_sample_db_test,
)
from exchange_rates_service import (
    get_latest_exchange_rates,
    get_latest_process_logs,
    load_latest_exchange_rates,
)
from exports import (
    sales_orders,
    customers,
    suppliers,
    products,
    warehouses,
    stock_on_hand,
    sales_shipments,
    credit_notes,
    invoices,
)

cfg = Config()

client = UnleashedClient(
    base_url=cfg.UNLEASHED_BASE_URL,
    api_id=cfg.UNLEASHED_API_ID,
    api_key=cfg.UNLEASHED_API_KEY,
    client_type=cfg.UNLEASHED_CLIENT_TYPE,
    timeout_seconds=cfg.REQUEST_TIMEOUT_SECONDS,
)

EXPORTS = {
    "products_api": {
        "category": "products",
        "label": "Products",
        "description": "Product master data",
        "sheet_name": "Products",
        "dummy": products.dummy,
        "api": lambda **kwargs: products.from_api(client, **kwargs),
    },
    "invoices": {
        "category": "sales",
        "label": "Invoices",
        "description": "Revenue documents (header-only for now)",
        "sheet_name": "Invoices",
        "dummy": invoices.dummy,
        "api": lambda **kwargs: invoices.from_api(client, **kwargs),
    },
    "credit_notes": {
        "category": "sales",
        "label": "Credit Notes",
        "description": "Returns and revenue corrections",
        "sheet_name": "CreditNotes",
        "dummy": credit_notes.dummy,
        "api": lambda **kwargs: credit_notes.from_api(client, **kwargs),
    },
    "warehouses": {
        "category": "inventory",
        "label": "Warehouses",
        "description": "Warehouse master data",
        "sheet_name": "Warehouses",
        "api": lambda **kwargs: warehouses.from_api(client, **kwargs),
    },
    "sales_shipments": {
        "category": "sales",
        "label": "Sales Shipments",
        "description": "Dispatch / fulfilment documents",
        "sheet_name": "SalesShipments",
        "dummy": sales_shipments.dummy,
        "api": lambda **kwargs: sales_shipments.from_api(client, **kwargs),
    },
    "stock_on_hand_api": {
        "category": "inventory",
        "label": "Stock On Hand (API)",
        "description": "Inventory snapshot (by product/warehouse)",
        "sheet_name": "StockOnHand",
        "api": lambda **kwargs: stock_on_hand.from_api(client, **kwargs),
    },
    "sales_orders": {
        "category": "sales",
        "label": "Sales Orders",
        "description": "Transactional",
        "sheet_name": "SalesOrders",
        "dummy": sales_orders.dummy,
        "api": lambda **kwargs: sales_orders.from_api(client, **kwargs),
    },
    "customers": {
        "category": "customers",
        "label": "Customers",
        "description": "Customer master data",
        "sheet_name": "Customers",
        "dummy": customers.dummy,
        "api": lambda **kwargs: customers.from_api(client, **kwargs),
    },
    "suppliers": {
        "category": "purchasing",
        "label": "Suppliers",
        "description": "Supplier master data",
        "sheet_name": "Suppliers",
        "dummy": suppliers.dummy,
        "api": lambda **kwargs: suppliers.from_api(client, **kwargs),
    },
}

# Placeholder reports for the dashboard (run via Azure SQL later; Run buttons are placeholders)
DASHBOARD_REPORTS = [
    {"key": "sales_summary", "label": "Sales Summary", "description": "Summary of sales and revenue from Unleashed data."},
    {"key": "inventory_report", "label": "Inventory Report", "description": "Stock levels and inventory position."},
    {"key": "customer_report", "label": "Customer Report", "description": "Customer list and sales dimensions."},
    {"key": "product_report", "label": "Product Report", "description": "Product master and cost foundation."},
    {"key": "purchasing_report", "label": "Purchasing Report", "description": "Suppliers and purchasing data."},
]


ILLEGAL_XLSX_CHARS_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


def _sanitize_excel_value(value: Any) -> Any:
    if isinstance(value, str):
        return ILLEGAL_XLSX_CHARS_RE.sub("", value)
    return value


def _sanitize_excel_row(row: List[Any]) -> List[Any]:
    return [_sanitize_excel_value(value) for value in row]


def build_workbook(selected_keys):
    wb = Workbook()
    wb.remove(wb.active)

    batch_t0 = time.perf_counter()
    company_for_run = "unleashed_client_1"
    log_info(
        f"Export workbook batch started: correlation_id={get_correlation_id()!r}, "
        f"selected_keys={selected_keys!r}, USE_UNLEASHED_API={cfg.USE_UNLEASHED_API}, client_configured={client.is_configured()}.",
        integration_name="unleashed_runner",
        module_name="app",
        function_name="build_workbook",
        event_type="export_batch_started",
        action="build_workbook",
        status="STARTED",
        detail="Each key maps to EXPORTS; API exports receive run_id when the callable accepts **kwargs. dbo.etl_run row is created when API mode is on and client is configured.",
    )

    run_id = None
    sync_run_id = str(uuid.uuid4())
    total_records = 0
    total_errors = 0
    critical_failed = False
    set_run_context(sync_run_id, company_for_run)
    try:
        start_sync_run(sync_run_id)
    except Exception as exc:
        log_warning(
            "sync_run start insert failed; continuing export flow without run table persistence.",
            integration_name="azure_sql",
            module_name="app",
            function_name="build_workbook",
            event_type="run_started",
            action="start_sync_run",
            entity_name="unleashed.sync_run",
            status="FAILED",
            detail=str(exc),
        )
    if cfg.USE_UNLEASHED_API and client.is_configured():
        try:
            run_id = start_run(company_id=company_for_run)
            sync_run_id = run_id
            set_run_context(sync_run_id, company_for_run)
            log_info(
                f"ETL run started: dbo.etl_run run_id={run_id!r}, company_id={company_for_run!r} (used for raw.api_payload and correlation in integration_log).",
                integration_name="azure_sql",
                module_name="app",
                function_name="build_workbook",
                event_type="run_started",
                action="start_run",
                entity_name="dbo.etl_run",
                status="SUCCESS",
                run_id=run_id,
                company_id=company_for_run,
            )
        except Exception as exc:
            run_id = None
            log_warning(
                "Could not insert dbo.etl_run row; proceeding without run_id (raw API payload logging to raw.api_payload will be skipped for this batch).",
                integration_name="azure_sql",
                module_name="app",
                function_name="build_workbook",
                event_type="run_start_failed",
                action="start_run",
                entity_name="dbo.etl_run",
                status="FAIL",
                detail=f"start_run raised: {exc!s}. Check dbo.etl_run table exists and DB user has INSERT. Next: fix schema or credentials.",
            )
    elif cfg.USE_UNLEASHED_API and not client.is_configured():
        log_warning(
            "USE_UNLEASHED_API is true but Unleashed client is missing base_url, api_id, api_key, or client_type; API exports will use dummy data.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="build_workbook",
            event_type="validation_warning",
            action="build_workbook",
            status="DEGRADED",
            detail="Set UNLEASHED_* environment variables and restart the app.",
        )

    workbook_batch_ref = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    log_info(
        f"Workbook generation started: batch_ref={workbook_batch_ref!r}, will create one sheet per successful export.",
        integration_name="unleashed_runner",
        module_name="app",
        function_name="build_workbook",
        event_type="workbook_generation_started",
        action="build_workbook",
        status="STARTED",
    )

    try:
        for key in selected_keys:
            if key not in EXPORTS:
                log_warning(
                    f"Skipping unknown export key {key!r} (not in EXPORTS registry).",
                    integration_name="unleashed_runner",
                    module_name="app",
                    function_name="build_workbook",
                    event_type="validation_warning",
                    action="build_workbook",
                    status="SKIPPED",
                    detail="Fix the form or caller to use a valid export key.",
                )
                continue

            export = EXPORTS.get(key)

            if not export:
                continue

            log_info(
                f"Export started for key {key!r}: resolving data source (generator, dummy, or Unleashed API).",
                integration_name="unleashed_runner",
                module_name="app",
                function_name="build_workbook",
                event_type="export_started",
                action="fetch_export_data",
                step_name=key,
                status="STARTED",
            )

            used_real_api = False
            fetch_t0 = time.perf_counter()
            if "generator" in export:
                sheet_name, headers, rows = export["generator"]()
                total_records += len(rows)
                log_info(
                    f"Export {key!r} used static generator path (not Unleashed API).",
                    integration_name="unleashed_runner",
                    module_name="app",
                    function_name="build_workbook",
                    event_type="export_data_source",
                    action="generator",
                    step_name=key,
                    status="SUCCESS",
                    record_count=len(rows),
                    duration_ms=int((time.perf_counter() - fetch_t0) * 1000),
                )
            else:
                if not cfg.USE_UNLEASHED_API or not client.is_configured():
                    sheet_name, headers, rows = export["dummy"]()
                    total_records += len(rows)
                    log_info(
                        f"Export {key!r} used built-in dummy data (API disabled or client not configured).",
                        integration_name="unleashed_runner",
                        module_name="app",
                        function_name="build_workbook",
                        event_type="export_data_source",
                        action="dummy",
                        step_name=key,
                        status="SUCCESS",
                        record_count=len(rows),
                        duration_ms=int((time.perf_counter() - fetch_t0) * 1000),
                    )
                else:
                    used_real_api = True
                    api_fn = export["api"]

                    try:
                        sheet_name, headers, rows = api_fn(
                            run_id=run_id, company_id=company_for_run
                        )
                    except TypeError:
                        log_warning(
                            f"Export {key!r} API callable does not accept run_id/company_id kwargs; calling with no args (raw payload may miss run_id).",
                            integration_name="unleashed_runner",
                            module_name="app",
                            function_name="build_workbook",
                            event_type="validation_warning",
                            action="fetch_export_data",
                            step_name=key,
                            status="DEGRADED",
                            detail="Update the lambda in EXPORTS to pass run_id and company_id into from_api for full raw logging.",
                        )
                        sheet_name, headers, rows = api_fn()

                    fetch_ms = int((time.perf_counter() - fetch_t0) * 1000)
                    total_records += len(rows)
                    log_info(
                        f"Export {key!r} completed Unleashed API path: sheet_name={sheet_name!r}, columns={len(headers)}, "
                        f"data_rows={len(rows)}, duration_ms={fetch_ms}.",
                        integration_name="unleashed_runner",
                        module_name="app",
                        function_name="build_workbook",
                        event_type="export_completed",
                        action="fetch_export_data",
                        step_name=key,
                        entity_name=sheet_name,
                        status="SUCCESS",
                        record_count=len(rows),
                        duration_ms=fetch_ms,
                    )

            ws = wb.create_sheet(title=sheet_name[:31])
            ws.append(_sanitize_excel_row(headers))
            for r in rows:
                ws.append(_sanitize_excel_row(r))

            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)

            for col_idx in range(1, len(headers) + 1):
                col_letter = get_column_letter(col_idx)
                max_len = 0
                for cell in ws[col_letter]:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

            log_info(
                f"Workbook sheet built: title={sheet_name[:31]!r}, columns={len(headers)}, data_rows={len(rows)}, "
                f"illegal control characters stripped for Excel compatibility.",
                integration_name="unleashed_runner",
                module_name="app",
                function_name="build_workbook",
                event_type="workbook_sheet_completed",
                action="build_workbook",
                entity_name=sheet_name,
                step_name=key,
                status="SUCCESS",
                record_count=len(rows),
            )

            if used_real_api and rows and sheet_name in ENDPOINT_TABLES:
                run_ref = f"FULL_{workbook_batch_ref}_{sheet_name}"
                started = datetime.utcnow()
                log_info(
                    f"Azure SQL sync starting after Excel sheet build: target unleashed.{sheet_name}, run_ref={run_ref!r}, "
                    f"rows_to_merge={len(rows)}, run_type=FULL.",
                    integration_name="unleashed_runner",
                    module_name="app",
                    function_name="build_workbook",
                    event_type="export_db_sync_started",
                    action="write_endpoint_rows",
                    entity_name=f"unleashed.{sheet_name}",
                    endpoint=sheet_name,
                    status="STARTED",
                    record_count=len(rows),
                    detail="write_endpoint_rows performs MERGE from session temp table; see unleashed_db integration_log events for timings.",
                )
                try:
                    write_result = write_endpoint_rows(
                        endpoint_name=sheet_name,
                        headers=headers,
                        rows=rows,
                        run_type="FULL",
                        run_ref=run_ref,
                    )
                    finished = datetime.utcnow()
                    n_written = write_result["rows_written"]
                    log_run(
                        {
                            "RunRef": run_ref,
                            "EndpointName": sheet_name,
                            "RunType": "FULL",
                            "RunMode": "excel_export_sync",
                            "Status": "PASS",
                            "StartedAt": started,
                            "FinishedAt": finished,
                            "DurationSeconds": int((finished - started).total_seconds()),
                            "RowsFetched": len(rows),
                            "RowsWritten": n_written,
                            "TargetTable": f"unleashed.{sheet_name}",
                            "Message": "Synced API export to Azure SQL.",
                            "TriggerSource": "excel_export",
                            "TriggeredBy": "ui",
                            "Environment": os.getenv("APP_ENV", "local"),
                        }
                    )
                    log_info(
                        f"Azure SQL sync completed for {sheet_name}: RunLog PASS, rows_written={n_written}, duration_s={int((finished - started).total_seconds())}.",
                        integration_name="unleashed_runner",
                        module_name="app",
                        function_name="build_workbook",
                        event_type="export_db_sync_completed",
                        action="write_endpoint_rows",
                        entity_name=f"unleashed.{sheet_name}",
                        endpoint=sheet_name,
                        status="SUCCESS",
                        record_count=n_written,
                        duration_ms=int((finished - started).total_seconds() * 1000),
                    )
                    update_endpoint_control(
                        sheet_name,
                        {
                            "LastFullRunRef": run_ref,
                            "LastFullRunAt": finished,
                            "LastRowCount": n_written,
                            "LastStatus": "PASS",
                            "NextAction": "Data available for reporting",
                        },
                    )
                except Exception as db_exc:
                    total_errors += 1
                    critical_failed = True
                    finished = datetime.utcnow()
                    log_error(
                        f"Azure SQL sync failed for sheet {sheet_name!r} (run_ref={run_ref!r}): MERGE/transaction error after Excel build.",
                        exc=db_exc,
                        integration_name="unleashed_runner",
                        module_name="app",
                        function_name="build_workbook",
                        event_type="export_db_sync_failed",
                        action="write_endpoint_rows",
                        entity_name=f"unleashed.{sheet_name}",
                        endpoint=sheet_name,
                        status="FAIL",
                        record_count=len(rows),
                        duration_ms=int((finished - started).total_seconds() * 1000),
                        detail="RunLog row will be written as FAIL; user sees error. Inspect unleashed_db and SQL error_message/stack_trace in integration_log.",
                    )
                    log_run(
                        {
                            "RunRef": run_ref,
                            "EndpointName": sheet_name,
                            "RunType": "FULL",
                            "RunMode": "excel_export_sync",
                            "Status": "FAIL",
                            "StartedAt": started,
                            "FinishedAt": finished,
                            "DurationSeconds": int((finished - started).total_seconds()),
                            "RowsFetched": len(rows),
                            "RowsWritten": 0,
                            "TargetTable": f"unleashed.{sheet_name}",
                            "Message": "Failed to sync export to Azure SQL.",
                            "ErrorMessage": str(db_exc),
                            "TriggerSource": "excel_export",
                            "TriggeredBy": "ui",
                            "Environment": os.getenv("APP_ENV", "local"),
                        }
                    )
                    raise
            elif used_real_api and rows and sheet_name not in ENDPOINT_TABLES:
                log_info(
                    f"No Azure SQL sync for sheet {sheet_name!r}: endpoint not in ENDPOINT_TABLES (Excel-only for this entity).",
                    integration_name="unleashed_runner",
                    module_name="app",
                    function_name="build_workbook",
                    event_type="export_db_sync_skipped",
                    action="write_endpoint_rows",
                    entity_name=sheet_name,
                    status="SKIPPED",
                    record_count=len(rows),
                )

        if run_id:
            finish_run(run_id, "SUCCESS")
            log_info(
                f"ETL run finished: run_id={run_id!r}, status=SUCCESS (dbo.etl_run updated).",
                integration_name="azure_sql",
                module_name="app",
                function_name="build_workbook",
                event_type="run_finished",
                action="finish_run",
                entity_name="dbo.etl_run",
                status="SUCCESS",
                run_id=run_id,
            )

        batch_ms = int((time.perf_counter() - batch_t0) * 1000)
        log_info(
            f"Export workbook batch completed successfully: sheets={wb.sheetnames!r}, total_duration_ms={batch_ms}.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="build_workbook",
            event_type="export_batch_completed",
            action="build_workbook",
            status="SUCCESS",
            duration_ms=batch_ms,
        )

        log_info(
            f"Workbook generation completed: {len(wb.sheetnames)} sheet(s) ready for save/download.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="build_workbook",
            event_type="workbook_generation_completed",
            action="build_workbook",
            status="SUCCESS",
            record_count=len(wb.sheetnames),
            duration_ms=batch_ms,
        )

        return wb

    except Exception as e:
        total_errors += 1
        critical_failed = True
        if run_id:
            finish_run(run_id, "FAILED", notes=str(e))
            log_error(
                f"ETL run finished: run_id={run_id!r}, status=FAILED - {e!s}.",
                exc=e,
                integration_name="azure_sql",
                module_name="app",
                function_name="build_workbook",
                event_type="run_finished",
                action="finish_run",
                entity_name="dbo.etl_run",
                status="FAIL",
                run_id=run_id,
                detail="Workbook build aborted; partial sheets may exist only in memory. Fix root cause and re-run export.",
            )
        else:
            log_error(
                f"Workbook build failed before or without dbo.etl_run: {e!s}.",
                exc=e,
                integration_name="unleashed_runner",
                module_name="app",
                function_name="build_workbook",
                event_type="export_batch_failed",
                action="build_workbook",
                status="FAIL",
            )
        raise
    finally:
        final_run_status = "FAILED" if critical_failed else "SUCCESS"
        try:
            finish_sync_run(
                run_id=sync_run_id,
                status=final_run_status,
                total_records=total_records,
                total_errors=total_errors,
            )
            log_info(
                f"sync_run finalized: run_id={sync_run_id!r}, status={final_run_status}, total_records={total_records}, total_errors={total_errors}.",
                integration_name="azure_sql",
                module_name="app",
                function_name="build_workbook",
                event_type="run_finished",
                action="finish_sync_run",
                entity_name="unleashed.sync_run",
                status=final_run_status,
                run_id=sync_run_id,
                record_count=total_records,
                detail="Run status is FAILED when any critical step fails; otherwise SUCCESS.",
            )
        except Exception as exc:
            log_warning(
                "sync_run finalize failed; execution results available in integration_log only.",
                integration_name="azure_sql",
                module_name="app",
                function_name="build_workbook",
                event_type="run_finished",
                action="finish_sync_run",
                entity_name="unleashed.sync_run",
                status="WARNING",
                run_id=sync_run_id,
                detail=str(exc),
            )
        clear_run_context()


def run_export(key: str, **kwargs):
    export = EXPORTS.get(key)
    if not export:
        raise KeyError(key)

    if "generator" in export:
        return export["generator"]()

    if not cfg.USE_UNLEASHED_API or not client.is_configured():
        return export["dummy"]()

    return export["api"](**kwargs)


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "unleashed-dev-secret")


@app.before_request
def _integration_log_begin():
    if get_correlation_id() is None:
        hdr = request.headers.get("X-Correlation-ID")
        cid = hdr.strip() if hdr and hdr.strip() else None
        set_correlation_id(cid)


@app.teardown_request
def _integration_log_end(_exc):
    clear_integration_request_context()


def _bootstrap_integration_logging() -> None:
    try:
        log_info(
            "Application startup: Unleashed Runner Flask process loaded; integration_log will record detailed events when AZURE_SQL_* is set and unleashed.integration_log exists.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="_bootstrap_integration_logging",
            event_type="application_startup",
            action="startup",
            status="STARTED",
            detail="Send X-Correlation-ID on requests to tie UI actions to log rows; run_id is set during API workbook exports.",
        )
        log_info(
            f"Configuration loaded (non-secret): USE_UNLEASHED_API={cfg.USE_UNLEASHED_API}, "
            f"UNLEASHED_BASE_URL={cfg.UNLEASHED_BASE_URL!r}, UNLEASHED_CLIENT_TYPE={'set' if cfg.UNLEASHED_CLIENT_TYPE else 'empty'}, "
            f"UNLEASHED_API_ID={'set' if bool(cfg.UNLEASHED_API_ID) else 'empty'} (identifier only; value not logged), "
            f"REQUEST_TIMEOUT_SECONDS={cfg.REQUEST_TIMEOUT_SECONDS}, APP_ENV={os.getenv('APP_ENV', 'local')!r}.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="_bootstrap_integration_logging",
            event_type="config_loaded",
            action="load_config",
            status="SUCCESS",
        )
        ping_database()
    except Exception:
        pass


_bootstrap_integration_logging()


def build_exports_list(category: Optional[str] = None):
    exports_list = []
    for key, meta in EXPORTS.items():
        if category and meta.get("category") != category:
            continue

        exports_list.append(
            {
                "key": key,
                "label": meta.get("label", key),
                "description": meta.get("description", ""),
                "last_run": "-",
                "status": "Idle",
                "status_class": "pill-neutral",
            }
        )
    return exports_list


def build_reports_list() -> List[Dict[str, Any]]:
    """Placeholder reports for dashboard and scheduler."""
    return list(DASHBOARD_REPORTS)


def get_report_label(key: str) -> str:
    for r in DASHBOARD_REPORTS:
        if r["key"] == key:
            return r["label"]
    return key


@app.route("/")
def index():
    reports = build_reports_list()
    try:
        schedules = list_schedules()
    except Exception:
        schedules = []
    for s in schedules:
        s["report_label"] = get_report_label(s["report_key"])
    return render_template(
        "index.html",
        active_page="dashboard",
        page_title="Dashboard",
        page_subtitle="Schedule and run Unleashed reports.",
        reports=reports,
        schedules=schedules,
    )


@app.route("/exports/<category>")
def exports_by_category(category: str):
    titles = {
        "sales": ("Sales & Revenue", "Sales documents and revenue drivers."),
        "customers": (
            "Customers & Sales Dimensions",
            "Customer master data and segmentation.",
        ),
        "products": (
            "Products & Cost Foundation",
            "Product master, groups, and pricing.",
        ),
        "inventory": ("Inventory", "Stock position and inventory movements."),
        "purchasing": ("Purchasing", "Supplier master and purchasing documents."),
    }
    title, subtitle = titles.get(
        category, ("Exports", "Run exports and download Excel-ready files.")
    )

    return render_template(
        "index.html",
        active_page=category,
        page_title=title,
        page_subtitle=subtitle,
        exports=build_exports_list(category=category),
    )


@app.route("/ui")
def ui_showcase():
    return render_template("ui_showcase.html", active_page="ui")


@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings")


@app.route("/unleashed/exchange-rates", methods=["GET"])
def unleashed_exchange_rates():
    rates = []
    logs = []
    page_error = None
    try:
        rates = get_latest_exchange_rates(limit=100)
    except Exception as exc:
        page_error = f"Could not read exchange rates: {exc}"
    try:
        logs = get_latest_process_logs(limit=25)
    except Exception as exc:
        page_error = (page_error + " | " if page_error else "") + f"Could not read process logs: {exc}"

    return render_template(
        "exchange_rates.html",
        active_page="exchange_rates",
        page_error=page_error,
        rates=rates,
        logs=logs,
    )


@app.route("/unleashed/exchange-rates/run", methods=["POST"])
def run_unleashed_exchange_rates():
    try:
        result = load_latest_exchange_rates()
        flash(
            "Exchange rates load succeeded: "
            f"{result['rows_loaded']} rate(s), date {result['rate_date']}, "
            f"base {result['base_currency']}, provider {result['provider']}.",
            "success",
        )
    except Exception as exc:
        flash(f"Exchange rates load failed: {exc}", "error")
    return redirect("/unleashed/exchange-rates")


def build_control_summary(endpoint_name: str = "SalesOrders") -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "LastRunRef": None,
        "LastStatus": None,
        "LastAssessmentStatus": None,
        "LastSignOffStatus": None,
        "LastCheckpoint": None,
        "LastRowCount": None,
        "RecentRuns": [],
    }
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT TOP 1
                    COALESCE([LastFullRunRef], [LastTestRunRef]),
                    [LastStatus],
                    [LastAssessmentStatus],
                    [LastSignOffStatus],
                    [LastCheckpoint],
                    [LastRowCount]
                FROM unleashed.EndpointControl
                WHERE [EndpointName] = ?
                """,
                endpoint_name,
            )
            row = cur.fetchone()
            if row:
                summary.update(
                    {
                        "LastRunRef": row[0],
                        "LastStatus": row[1],
                        "LastAssessmentStatus": row[2],
                        "LastSignOffStatus": row[3],
                        "LastCheckpoint": row[4],
                        "LastRowCount": row[5],
                    }
                )
            cur.execute(
                """
                SELECT TOP 8
                    [RunRef], [RunMode], [Status], [RowsFetched], [RowsWritten], [RowsDeleted], [FinishedAt], [ErrorMessage]
                FROM unleashed.RunLog
                WHERE [EndpointName] IN (?, 'ConnectionTest')
                ORDER BY [CreatedAt] DESC
                """,
                endpoint_name,
            )
            summary["RecentRuns"] = cur.fetchall()
    except Exception:
        pass
    return summary


def verify_last_run_in_db(endpoint_name: str = "SalesOrders") -> Dict[str, Any]:
    table_name = f"unleashed.{endpoint_name}"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP 1
                [RunRef], [Status], [RowsFetched], [RowsWritten], [RowsDeleted], [RunMode], [ErrorMessage], [FinishedAt], [RunType]
            FROM unleashed.RunLog
            WHERE [EndpointName] = ?
            ORDER BY [CreatedAt] DESC
            """,
            endpoint_name,
        )
        row = cur.fetchone()
        if not row:
            return {
                "status": "FAIL",
                "message": f"No run log found for {endpoint_name}.",
                "verified": False,
            }

        run_ref = row[0]
        run_status = row[1]
        logged_rows_written = row[3] if row[3] is not None else 0
        run_mode = row[5]
        error_message = row[6]
        run_type_expected = row[8] or "TEST"

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE [RunRef] = ? AND [EndpointName] = ? AND [RunType] = ?
            """,
            run_ref,
            endpoint_name,
            run_type_expected,
        )
        actual_rows = cur.fetchone()[0]
        verified = (run_status == "PASS") and (actual_rows == logged_rows_written)
        status = "PASS" if verified else "FAIL"
        message = (
            f"Verified run {run_ref}. Logged rows={logged_rows_written}, DB rows={actual_rows}."
            if verified
            else f"Verification mismatch for run {run_ref}. Logged rows={logged_rows_written}, DB rows={actual_rows}."
        )
        if error_message:
            message = f"{message} Last error: {error_message}"

        return {
            "status": status,
            "verified": verified,
            "message": message,
            "run_ref": run_ref,
            "rows_written": actual_rows,
            "records_processed": row[2],
            "rows_deleted": row[4],
            "run_mode": run_mode,
            "finished_at": row[7],
        }


@app.route("/data-control", methods=["GET", "POST"])
def data_control_center():
    endpoint_name = request.form.get("endpoint_name", "SalesOrders")
    action = request.form.get("action")
    result: Dict[str, Any] = {}

    if request.method == "POST" and action:
        log_info(
            f"Data control POST: action={action!r}, endpoint_name={endpoint_name!r}, correlation_id={get_correlation_id()!r}.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="data_control_center",
            event_type="data_control_action",
            action=action,
            entity_name=endpoint_name,
            status="STARTED",
        )
        try:
            if action == "test_db_connection":
                result = run_connection_test(triggered_by="ui")
            elif action == "clear_connection_test_data":
                result = clear_connection_test(triggered_by="ui")
            elif action == "run_sample_db_test":
                result = run_sample_db_test(endpoint_name=endpoint_name, triggered_by="ui")
            elif action == "clear_test_rows":
                result = clear_test_rows(endpoint_name=endpoint_name, triggered_by="ui")
            elif action == "clear_endpoint_reset":
                confirm = request.form.get("confirm_clear_endpoint", "")
                if confirm == "YES_CLEAR":
                    result = clear_endpoint_for_production_reset(endpoint_name=endpoint_name, triggered_by="ui")
                else:
                    result = {"status": "FAIL", "error": "Confirmation required (type YES_CLEAR)."}
                    log_warning(
                        "clear_endpoint_reset rejected: confirmation token YES_CLEAR not submitted.",
                        integration_name="unleashed_runner",
                        module_name="app",
                        function_name="data_control_center",
                        event_type="validation_warning",
                        action="clear_endpoint_reset",
                        entity_name=endpoint_name,
                        status="FAIL",
                    )
            elif action == "verify_last_run":
                result = verify_last_run_in_db(endpoint_name=endpoint_name)
            else:
                result = {"status": "FAIL", "error": "Unknown action."}
                log_warning(
                    f"Data control unknown action {action!r}.",
                    integration_name="unleashed_runner",
                    module_name="app",
                    function_name="data_control_center",
                    event_type="validation_warning",
                    action=str(action),
                    status="FAIL",
                )
        except SetupRequiredError as exc:
            log_error(
                f"Data control action {action!r} blocked: database setup incomplete for {endpoint_name!r}.",
                exc=exc,
                integration_name="unleashed_runner",
                module_name="app",
                function_name="data_control_center",
                event_type="data_control_failed",
                action=str(action),
                entity_name=endpoint_name,
                status="FAIL",
                detail=str(exc),
            )
            result = {"status": "FAIL", "error": f"Database setup required: {exc}"}
        except Exception as exc:
            log_error(
                f"Data control action {action!r} raised an unexpected exception.",
                exc=exc,
                integration_name="unleashed_runner",
                module_name="app",
                function_name="data_control_center",
                event_type="data_control_failed",
                action=str(action),
                entity_name=endpoint_name,
                status="FAIL",
            )
            result = {"status": "FAIL", "error": str(exc)}

    return render_template(
        "data_control_center.html",
        active_page="data_control_center",
        endpoint_name=endpoint_name,
        endpoints=["SalesOrders"],
        result=result,
        summary=build_control_summary(endpoint_name),
    )


@app.route("/api-status")
def api_status():
    return {
        "use_unleashed_api": cfg.USE_UNLEASHED_API,
        "configured": client.is_configured(),
        "base_url": client.base_url,
        "client_type": client.client_type,
    }


@app.route("/run-selected", methods=["POST"])
def run_selected():
    selected = request.form.getlist("exports")
    if not selected:
        log_warning(
            "run-selected rejected: no exports in form submission.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="run_selected",
            event_type="file_download_skipped",
            action="run_selected",
            status="FAIL",
        )
        return "No exports selected", 400

    t0 = time.perf_counter()
    wb = build_workbook(selected)
    build_ms = int((time.perf_counter() - t0) * 1000)

    buf = io.BytesIO()
    save_t0 = time.perf_counter()
    wb.save(buf)
    save_ms = int((time.perf_counter() - save_t0) * 1000)
    buf.seek(0)
    body = buf.getvalue()
    payload_len = len(body)

    log_info(
        f"File download triggered: unleashed_exports.xlsx (multi-export), correlation_id={get_correlation_id()!r}, "
        f"exports={selected!r}, sheets={wb.sheetnames!r}, build_duration_ms={build_ms}, xlsx_save_duration_ms={save_ms}, "
        f"response_body_bytes~{payload_len}.",
        integration_name="unleashed_runner",
        module_name="app",
        function_name="run_selected",
        event_type="file_download_triggered",
        action="run_selected",
        status="SUCCESS",
        record_count=len(wb.sheetnames),
        duration_ms=build_ms + save_ms,
        detail="Client should receive attachment; if browser blocks download, check pop-up settings.",
    )

    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=unleashed_exports.xlsx"},
    )


@app.route("/run-single", methods=["POST"])
def run_single():
    key = request.form.get("export")
    if key not in EXPORTS:
        log_warning(
            f"run-single rejected: invalid export key {key!r}.",
            integration_name="unleashed_runner",
            module_name="app",
            function_name="run_single",
            event_type="file_download_skipped",
            action="run_single",
            status="FAIL",
        )
        return "Invalid export", 400

    t0 = time.perf_counter()
    wb = build_workbook([key])
    build_ms = int((time.perf_counter() - t0) * 1000)

    buf = io.BytesIO()
    save_t0 = time.perf_counter()
    wb.save(buf)
    save_ms = int((time.perf_counter() - save_t0) * 1000)
    buf.seek(0)
    body = buf.getvalue()
    payload_len = len(body)

    log_info(
        f"File download triggered: {key}.xlsx, correlation_id={get_correlation_id()!r}, sheets={wb.sheetnames!r}, "
        f"build_duration_ms={build_ms}, xlsx_save_duration_ms={save_ms}, response_body_bytes~{payload_len}.",
        integration_name="unleashed_runner",
        module_name="app",
        function_name="run_single",
        event_type="file_download_triggered",
        action="run_single",
        step_name=key,
        status="SUCCESS",
        record_count=len(wb.sheetnames),
        duration_ms=build_ms + save_ms,
    )

    return Response(
        body,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={key}.xlsx"},
    )


@app.route("/schedule/add", methods=["POST"])
def schedule_add():
    report_key = request.form.get("report_key")
    frequency = request.form.get("frequency", "weekly").strip() or "weekly"
    valid_keys = {r["key"] for r in DASHBOARD_REPORTS}
    if not report_key or report_key not in valid_keys:
        return "Invalid report", 400
    add_schedule(report_key, frequency)
    return redirect("/")


@app.route("/schedule/<schedule_id>/delete", methods=["POST"])
def schedule_delete(schedule_id: str):
    delete_schedule(schedule_id)
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)


