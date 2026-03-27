from dotenv import load_dotenv
from db import start_run, finish_run
from schedules import add_schedule, delete_schedule, list_schedules

load_dotenv()

from flask import Flask, redirect, render_template, request, Response
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import io
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, List

from config import Config
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
        "api": lambda: products.from_api(client),
    },
    "invoices": {
        "category": "sales",
        "label": "Invoices",
        "description": "Revenue documents (header-only for now)",
        "sheet_name": "Invoices",
        "dummy": invoices.dummy,
        "api": lambda: invoices.from_api(client),
    },
    "credit_notes": {
        "category": "sales",
        "label": "Credit Notes",
        "description": "Returns and revenue corrections",
        "sheet_name": "CreditNotes",
        "dummy": credit_notes.dummy,
        "api": lambda: credit_notes.from_api(client),
    },
    "warehouses": {
        "category": "inventory",
        "label": "Warehouses",
        "description": "Warehouse master data",
        "sheet_name": "Warehouses",
        "api": lambda: warehouses.from_api(client),
    },
    "sales_shipments": {
        "category": "sales",
        "label": "Sales Shipments",
        "description": "Dispatch / fulfilment documents",
        "sheet_name": "SalesShipments",
        "dummy": sales_shipments.dummy,
        "api": lambda: sales_shipments.from_api(client),
    },
    "stock_on_hand_api": {
        "category": "inventory",
        "label": "Stock On Hand (API)",
        "description": "Inventory snapshot (by product/warehouse)",
        "sheet_name": "StockOnHand",
        "api": lambda: stock_on_hand.from_api(client),
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
        "api": lambda: customers.from_api(client),
    },
    "suppliers": {
        "category": "purchasing",
        "label": "Suppliers",
        "description": "Supplier master data",
        "sheet_name": "Suppliers",
        "dummy": suppliers.dummy,
        "api": lambda: suppliers.from_api(client),
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


def build_workbook(selected_keys):
    wb = Workbook()
    wb.remove(wb.active)

    run_id = None
    if cfg.USE_UNLEASHED_API and client.is_configured():
        try:
            run_id = start_run(company_id="unleashed_client_1")
        except Exception:
            run_id = None

    workbook_batch_ref = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    try:
        for key in selected_keys:
            if key not in EXPORTS:
                continue

            export = EXPORTS.get(key)

            if not export:
                continue

            used_real_api = False
            if "generator" in export:
                sheet_name, headers, rows = export["generator"]()
            else:
                if not cfg.USE_UNLEASHED_API or not client.is_configured():
                    sheet_name, headers, rows = export["dummy"]()
                else:
                    used_real_api = True
                    api_fn = export["api"]

                    try:
                        sheet_name, headers, rows = api_fn(
                            run_id=run_id, company_id="unleashed_client_1"
                        )
                    except TypeError:
                        sheet_name, headers, rows = api_fn()

            ws = wb.create_sheet(title=sheet_name[:31])
            ws.append(headers)
            for r in rows:
                ws.append(r)

            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)

            for col_idx in range(1, len(headers) + 1):
                col_letter = get_column_letter(col_idx)
                max_len = 0
                for cell in ws[col_letter]:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

            if used_real_api and rows and sheet_name in ENDPOINT_TABLES:
                run_ref = f"FULL_{workbook_batch_ref}_{sheet_name}"
                started = datetime.utcnow()
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
                    finished = datetime.utcnow()
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

        if run_id:
            finish_run(run_id, "SUCCESS")

        return wb

    except Exception as e:
        if run_id:
            finish_run(run_id, "FAILED", notes=str(e))
        raise


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
                "last_run": "—",
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
            elif action == "verify_last_run":
                result = verify_last_run_in_db(endpoint_name=endpoint_name)
            else:
                result = {"status": "FAIL", "error": "Unknown action."}
        except SetupRequiredError as exc:
            result = {"status": "FAIL", "error": f"Database setup required: {exc}"}
        except Exception as exc:
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
        return "No exports selected", 400

    wb = build_workbook(selected)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=unleashed_exports.xlsx"},
    )


@app.route("/run-single", methods=["POST"])
def run_single():
    key = request.form.get("export")
    if key not in EXPORTS:
        return "Invalid export", 400

    wb = build_workbook([key])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return Response(
        buf.getvalue(),
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
