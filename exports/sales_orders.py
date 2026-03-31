from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.paging import fetch_all_pages
from exports.utils import parse_unleashed_dotnet_date

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "SalesOrders", ["Order Number", "Customer", "Total", "Status"], [
        ["SO-1001", "Cafe Nero", 2450.00, "Completed"],
        ["SO-1002", "Coffee Corner", 1320.00, "Pending"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    pages = fetch_all_pages(
        client,
        "/SalesOrders",
        endpoint="SalesOrders",
        run_id=run_id,
        company_id=company_id,
    )

    headers = [
        "OrderNumber",
        "OrderDate",
        "RequiredDate",
        "CompletedDate",
        "ReceivedDate",
        "OrderStatus",
        "CustomerName",
        "CustomerGuid",
        "CustomerRef",
        "Warehouse",
        "WarehouseGuid",
        "Currency",
        "ExchangeRate",
        "SubTotal",
        "TaxTotal",
        "Total",
        "OrderGuid",
        "LastModifiedOn",
        "LineNumber",
        "ProductCode",
        "ProductDescription",
        "ProductGuid",
        "DueDate",
        "OrderQuantity",
        "UnitPrice",
        "LineTotal",
        "LineTax",
        "LineGuid",
        "LineLastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for data in pages:
        for order in data.get("Items", []):
            for line in (order.get("SalesOrderLines") or []):
                rows.append([
                    order.get("OrderNumber"),
                    parse_unleashed_dotnet_date(order.get("OrderDate")),
                    parse_unleashed_dotnet_date(order.get("RequiredDate")),
                    parse_unleashed_dotnet_date(order.get("CompletedDate")),
                    parse_unleashed_dotnet_date(order.get("ReceivedDate")),
                    order.get("OrderStatus"),
                    (order.get("Customer") or {}).get("CustomerName"),
                    (order.get("Customer") or {}).get("Guid"),
                    order.get("CustomerRef"),
                    (order.get("Warehouse") or {}).get("WarehouseName"),
                    (order.get("Warehouse") or {}).get("Guid"),
                    (order.get("Currency") or {}).get("CurrencyCode"),
                    order.get("ExchangeRate"),
                    order.get("SubTotal"),
                    order.get("TaxTotal"),
                    order.get("Total"),
                    order.get("Guid"),
                    parse_unleashed_dotnet_date(order.get("LastModifiedOn")),
                    line.get("LineNumber"),
                    (line.get("Product") or {}).get("ProductCode"),
                    (line.get("Product") or {}).get("ProductDescription"),
                    (line.get("Product") or {}).get("Guid"),
                    parse_unleashed_dotnet_date(line.get("DueDate")),
                    line.get("OrderQuantity"),
                    line.get("UnitPrice"),
                    line.get("LineTotal"),
                    line.get("LineTax"),
                    line.get("Guid"),
                    parse_unleashed_dotnet_date(line.get("LastModifiedOn")),
                ])

    return "SalesOrders", headers, rows
