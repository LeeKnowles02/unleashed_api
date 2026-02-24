from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date
from exports.utils_db import try_insert_raw

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "StockOnHand", ["ProductCode", "WarehouseName", "QtyOnHand"], [
        ["P001", "Main Warehouse", 340],
        ["P002", "Main Warehouse", 120],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    data: Dict[str, Any] = client.get("/StockOnHand")
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint="StockOnHand",
        http_status=getattr(client, "last_status_code", None),
        payload_obj=data,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
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

    for item in data.get("Items", []):
        product = item.get("Product")
        warehouse = item.get("Warehouse")

        product_code = product.get("ProductCode") if isinstance(product, dict) else product
        product_desc = product.get("ProductDescription") if isinstance(product, dict) else None
        product_guid = product.get("Guid") if isinstance(product, dict) else None

        wh_name = warehouse.get("WarehouseName") if isinstance(warehouse, dict) else warehouse
        wh_guid = warehouse.get("Guid") if isinstance(warehouse, dict) else None

        rows.append([
            product_code,
            product_desc,
            product_guid,
            wh_name,
            wh_guid,
            item.get("QtyOnHand"),
            item.get("QtyAllocated"),
            item.get("QtyAvailable"),
            item.get("QtyOnPurchase"),
            item.get("QtyOnSalesOrder"),
            item.get("AvgLandCost"),
            item.get("TotalValue"),
            parse_unleashed_dotnet_date(item.get("LastModifiedOn")),
        ])

    return "StockOnHand", headers, rows
