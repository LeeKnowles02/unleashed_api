import time
from typing import Any, Dict, List, Tuple, Optional

from unleashed_client import UnleashedClient
from exports.paging import fetch_all_pages
from exports.utils import parse_unleashed_dotnet_date
from integration_log_writer import log_error, log_info

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
    n_pages = len(pages)
    log_info(
        f"Transformation started: SalesOrders — exploding SalesOrderLines to flat rows from {n_pages} page(s) "
        f"(run_id={run_id!r}); one output row per line.",
        integration_name="unleashed_api",
        module_name="exports.sales_orders",
        function_name="from_api",
        event_type="transformation_started",
        action="map_api_to_rows",
        entity_name="SalesOrders",
        endpoint="/SalesOrders",
        status="STARTED",
        record_count=n_pages,
        detail="Orders without lines produce zero rows for that order; check Unleashed if line counts seem low.",
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
    t0 = time.perf_counter()

    try:
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
    except Exception as exc:
        log_error(
            f"Transformation failed: SalesOrders — error while flattening orders/lines after {int((time.perf_counter() - t0) * 1000)} ms.",
            exc=exc,
            integration_name="unleashed_api",
            module_name="exports.sales_orders",
            function_name="from_api",
            event_type="transformation_failed",
            action="map_api_to_rows",
            entity_name="SalesOrders",
            endpoint="/SalesOrders",
            status="FAIL",
            detail="Validate SalesOrderLines and nested Customer/Warehouse/Product objects in API payload.",
        )
        raise

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_info(
        f"Transformation completed: SalesOrders — produced {len(rows)} line-row(s) from {n_pages} page(s) in {elapsed_ms} ms.",
        integration_name="unleashed_api",
        module_name="exports.sales_orders",
        function_name="from_api",
        event_type="transformation_completed",
        action="map_api_to_rows",
        entity_name="SalesOrders",
        endpoint="/SalesOrders",
        status="SUCCESS",
        record_count=len(rows),
        duration_ms=elapsed_ms,
    )

    return "SalesOrders", headers, rows
