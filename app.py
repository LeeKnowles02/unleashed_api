from flask import Flask, render_template, request, Response
import csv
import io
import zipfile

def products_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Product Code", "Product Name", "Category", "Price"])
    writer.writerow(["P001", "Espresso Beans", "Coffee", 120.00])
    writer.writerow(["P002", "Milk Powder", "Consumables", 85.50])

    return output.getvalue()


def stock_on_hand_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Product Code", "Warehouse", "Quantity"])
    writer.writerow(["P001", "Main Warehouse", 340])
    writer.writerow(["P002", "Main Warehouse", 120])

    return output.getvalue()


def sales_orders_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Order Number", "Customer", "Total", "Status"])
    writer.writerow(["SO-1001", "Cafe Nero", 2450.00, "Completed"])
    writer.writerow(["SO-1002", "Coffee Corner", 1320.00, "Pending"])

    return output.getvalue()

EXPORTS = {
    "products": {
        "filename": "products.csv",
        "generator": products_csv,
    },
    "stock_on_hand": {
        "filename": "stock_on_hand.csv",
        "generator": stock_on_hand_csv,
    },
    "sales_orders": {
        "filename": "sales_orders.csv",
        "generator": sales_orders_csv,
    },
}

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", active_page="dashboard")

@app.route("/ui")
def ui_showcase():
    return render_template("ui_showcase.html", active_page="ui")

if __name__ == "__main__":
    app.run(debug=True)
