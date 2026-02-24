from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date
from exports.utils_db import try_insert_raw

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "Invoices", ["InvoiceNumber", "CustomerName", "InvoiceDate", "Total", "Guid"], [
        ["INV-1001", "Cafe Nero", None, 2450.00, "00000000-0000-0000-0000-000000000001"],
        ["INV-1002", "Coffee Corner", None, 1320.00, "00000000-0000-0000-0000-000000000002"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    data: Dict[str, Any] = client.get("/Invoices")
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint="Invoices",
        http_status=getattr(client, "last_status_code", None),
        payload_obj=data,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
    )
    headers = [
        "InvoiceNumber",
        "InvoiceDate",
        "DueDate",
        "Status",
        "CustomerName",
        "CustomerCode",
        "CustomerGuid",
        "Currency",
        "ExchangeRate",
        "SubTotal",
        "TaxTotal",
        "Total",
        "SalesOrderNumber",
        "SalesOrderGuid",
        "WarehouseName",
        "WarehouseGuid",
        "Guid",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for inv in data.get("Items", []):
        customer = inv.get("Customer")
        currency = inv.get("Currency")
        sales_order = inv.get("SalesOrder")
        warehouse = inv.get("Warehouse")

        cust_name = customer.get("CustomerName") if isinstance(customer, dict) else customer
        cust_code = customer.get("CustomerCode") if isinstance(customer, dict) else None
        cust_guid = customer.get("Guid") if isinstance(customer, dict) else None

        currency_code = currency.get("CurrencyCode") if isinstance(currency, dict) else currency

        so_number = sales_order.get("OrderNumber") if isinstance(sales_order, dict) else sales_order
        so_guid = sales_order.get("Guid") if isinstance(sales_order, dict) else None

        wh_name = warehouse.get("WarehouseName") if isinstance(warehouse, dict) else warehouse
        wh_guid = warehouse.get("Guid") if isinstance(warehouse, dict) else None

        rows.append([
            inv.get("InvoiceNumber"),
            parse_unleashed_dotnet_date(inv.get("InvoiceDate")),
            parse_unleashed_dotnet_date(inv.get("DueDate")),
            inv.get("Status"),
            cust_name,
            cust_code,
            cust_guid,
            currency_code,
            inv.get("ExchangeRate"),
            inv.get("SubTotal"),
            inv.get("TaxTotal"),
            inv.get("Total"),
            so_number,
            so_guid,
            wh_name,
            wh_guid,
            inv.get("Guid"),
            parse_unleashed_dotnet_date(inv.get("LastModifiedOn")),
        ])

    return "Invoices", headers, rows
