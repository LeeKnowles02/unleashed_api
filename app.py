from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, Response
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import io
from typing import Any, Dict, Optional, List

from config import Config
from unleashed_client import UnleashedClient
from exports import sales_orders, customers, suppliers


def products_dummy():
    return (
        "Products",
        ["Product Code", "Product Name", "Category", "Price"],
        [
            ["P001", "Espresso Beans", "Coffee", 120.00],
            ["P002", "Milk Powder", "Consumables", 85.50],
        ],
    )


def stock_on_hand_dummy():
    return (
        "StockOnHand",
        ["Product Code", "Warehouse", "Quantity"],
        [
            ["P001", "Main Warehouse", 340],
            ["P002", "Main Warehouse", 120],
        ],
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
    "products": {
        "category": "products",
        "label": "Products",
        "description": "Master data",
        "sheet_name": "Products",
        "generator": products_dummy,
    },
    "stock_on_hand": {
        "category": "inventory",
        "label": "Stock on Hand",
        "description": "Inventory snapshot",
        "sheet_name": "StockOnHand",
        "generator": stock_on_hand_dummy,
    },
    "sales_orders": {
        "category": "sales",
        "label": "Sales Orders",
        "description": "Transactional",
        "sheet_name": "SalesOrders",
        "dummy": sales_orders.dummy,
        "api": lambda: sales_orders.from_api(client),
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


def run_export(key: str):
    export = EXPORTS.get(key)
    if not export:
        raise KeyError(key)

    if "generator" in export:
        return export["generator"]()

    if not cfg.USE_UNLEASHED_API or not client.is_configured():
        return export["dummy"]()

    return export["api"]()


def build_workbook(selected_keys):
    wb = Workbook()
    wb.remove(wb.active)

    for key in selected_keys:
        if key not in EXPORTS:
            continue

        sheet_name, headers, rows = run_export(key)

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

    return wb


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


@app.route("/")
def index():
    return render_template(
        "index.html",
        active_page="dashboard",
        page_title="Dashboard",
        page_subtitle="Run exports and download Excel-ready files.",
        exports=build_exports_list(),
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


if __name__ == "__main__":
    app.run(debug=True)
