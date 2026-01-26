from typing import List, Any, Tuple
from . import ExportResult

def dummy() -> ExportResult:
    return "Products", ["Product Code", "Product Name", "Category", "Price"], [
        ["P001", "Espresso Beans", "Coffee", 120.00],
        ["P002", "Milk Powder", "Consumables", 85.50],
    ]

def from_api(client) -> ExportResult:
    """
    Placeholder for Unleashed API integration.
    Tonight you’ll provide endpoint + required fields.
    """
    # Example idea (do not run yet):
    # data = client.get("/Products", params={"pageSize": 200, "page": 1})
    raise NotImplementedError("Products API export not implemented yet.")
