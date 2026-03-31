from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.paging import fetch_all_pages
from exports.utils import parse_unleashed_dotnet_date

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "StockOnHand", ["ProductCode", "WarehouseName", "QtyOnHand"], [
        ["P001", "Main Warehouse", 340],
        ["P002", "Main Warehouse", 120],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    pages = fetch_all_pages(
        client,
        "/StockOnHand",
        endpoint="StockOnHand",
        run_id=run_id,
        company_id=company_id,
    )
    headers = [
        "ProductCode",
        "ProductDescription",
        "ProductGuid",
        "WarehouseName",
        "WarehouseGuid",
        "QtyOnHand",
        "QtyAllocated",
        "QtyAvailable",
        "QtyOnPurchase",
        "QtyOnSalesOrder",
        "AvgLandCost",
        "TotalValue",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for data in pages:
        for item in data.get("Items", []):
            product = item.get("Product")
            warehouse = item.get("Warehouse")

            product_code = item.get("ProductCode") or (product.get("ProductCode") if isinstance(product, dict) else product)
            product_desc = item.get("ProductDescription") or (product.get("ProductDescription") if isinstance(product, dict) else None)
            product_guid = item.get("ProductGuid") or (product.get("Guid") if isinstance(product, dict) else None) or item.get("Guid") or ""

            wh_name = item.get("WarehouseName") or item.get("Warehouse") or (warehouse.get("WarehouseName") if isinstance(warehouse, dict) else warehouse) or ""
            wh_guid = item.get("WarehouseGuid") or item.get("WarehouseId") or (warehouse.get("Guid") if isinstance(warehouse, dict) else None) or ""

            rows.append([
                product_code,
                product_desc,
                product_guid,
                wh_name,
                wh_guid,
                item.get("QtyOnHand"),
                item.get("AllocatedQty", item.get("QtyAllocated")),
                item.get("AvailableQty", item.get("QtyAvailable")),
                item.get("OnPurchase", item.get("QtyOnPurchase")),
                item.get("QtyOnSalesOrder"),
                item.get("AvgCost", item.get("AvgLandCost")),
                item.get("TotalCost", item.get("TotalValue")),
                parse_unleashed_dotnet_date(item.get("LastModifiedOn")),
            ])

    return "StockOnHand", headers, rows
