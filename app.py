from flask import Flask, render_template, request, Response
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import io


# ---------- Dummy data providers (sheet_name, headers, rows) ----------

def products_data():
    return "Products", ["Product Code", "Product Name", "Category", "Price"], [
        ["P001", "Espresso Beans", "Coffee", 120.00],
        ["P002", "Milk Powder", "Consumables", 85.50],
    ]


def stock_on_hand_data():
    return "StockOnHand", ["Product Code", "Warehouse", "Quantity"], [
        ["P001", "Main Warehouse", 340],
        ["P002", "Main Warehouse", 120],
    ]


def sales_orders_data():
    return "SalesOrders", ["Order Number", "Customer", "Total", "Status"], [
        ["SO-1001", "Cafe Nero", 2450.00, "Completed"],
        ["SO-1002", "Coffee Corner", 1320.00, "Pending"],
    ]


EXPORTS = {
    "products": {"generator": products_data},
    "stock_on_hand": {"generator": stock_on_hand_data},
    "sales_orders": {"generator": sales_orders_data},
}


# ---------- Workbook builder (multi-sheet) ----------

def build_workbook(selected_keys):
    wb = Workbook()
    wb.remove(wb.active)

    for key in selected_keys:
        export = EXPORTS.get(key)
        if not export:
            continue

        sheet_name, headers, rows = export["generator"]()

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


@app.route("/")
def index():
    return render_template("index.html", active_page="dashboard")


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
