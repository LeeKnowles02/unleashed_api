from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date
from exports.utils_db import try_insert_raw

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "SalesShipments", ["ShipmentNumber", "CustomerName", "ShipmentDate", "Guid"], [
        ["SS-1001", "Cafe Nero", None, "00000000-0000-0000-0000-000000000001"],
        ["SS-1002", "Coffee Corner", None, "00000000-0000-0000-0000-000000000002"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    data: Dict[str, Any] = client.get("/SalesShipments")
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint="SalesShipments",
        http_status=getattr(client, "last_status_code", None),
        payload_obj=data,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
    )
    headers = [
        "ShipmentNumber",
        "ShipmentDate",
        "ShipmentStatus",
        "SalesOrderNumber",
        "SalesOrderGuid",
        "CustomerName",
        "CustomerCode",
        "CustomerGuid",
        "WarehouseName",
        "WarehouseGuid",
        "Carrier",
        "TrackingNumber",
        "Guid",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for s in data.get("Items", []):
        customer = s.get("Customer")
        warehouse = s.get("Warehouse")
        sales_order = s.get("SalesOrder")

        # tolerate dict or string shapes
        cust_name = customer.get("CustomerName") if isinstance(customer, dict) else customer
        cust_code = customer.get("CustomerCode") if isinstance(customer, dict) else None
        cust_guid = customer.get("Guid") if isinstance(customer, dict) else None

        wh_name = warehouse.get("WarehouseName") if isinstance(warehouse, dict) else warehouse
        wh_guid = warehouse.get("Guid") if isinstance(warehouse, dict) else None

        so_number = sales_order.get("OrderNumber") if isinstance(sales_order, dict) else sales_order
        so_guid = sales_order.get("Guid") if isinstance(sales_order, dict) else None

        rows.append([
            s.get("ShipmentNumber"),
            parse_unleashed_dotnet_date(s.get("ShipmentDate")),
            s.get("ShipmentStatus"),
            so_number,
            so_guid,
            cust_name,
            cust_code,
            cust_guid,
            wh_name,
            wh_guid,
            s.get("Carrier"),
            s.get("TrackingNumber"),
            s.get("Guid"),
            parse_unleashed_dotnet_date(s.get("LastModifiedOn")),
        ])

    return "SalesShipments", headers, rows
