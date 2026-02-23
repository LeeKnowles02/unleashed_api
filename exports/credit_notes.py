from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date
from exports.utils_db import try_insert_raw

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "CreditNotes", ["CreditNoteNumber", "CustomerName", "CreditNoteDate", "Total", "Guid"], [
        ["CN-1001", "Cafe Nero", None, 250.00, "00000000-0000-0000-0000-000000000001"],
        ["CN-1002", "Coffee Corner", None, 120.00, "00000000-0000-0000-0000-000000000002"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    data: Dict[str, Any] = client.get("/CreditNotes")
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint="CreditNotes",
        http_status=getattr(client, "last_status_code", None),
        payload_obj=data,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
    )
    headers = [
        "CreditNoteNumber",
        "CreditNoteDate",
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
        "InvoiceNumber",
        "InvoiceGuid",
        "Guid",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for cn in data.get("Items", []):
        customer = cn.get("Customer")
        currency = cn.get("Currency")
        sales_order = cn.get("SalesOrder")
        invoice = cn.get("Invoice")

        cust_name = customer.get("CustomerName") if isinstance(customer, dict) else customer
        cust_code = customer.get("CustomerCode") if isinstance(customer, dict) else None
        cust_guid = customer.get("Guid") if isinstance(customer, dict) else None

        currency_code = currency.get("CurrencyCode") if isinstance(currency, dict) else currency

        so_number = sales_order.get("OrderNumber") if isinstance(sales_order, dict) else sales_order
        so_guid = sales_order.get("Guid") if isinstance(sales_order, dict) else None

        inv_number = invoice.get("InvoiceNumber") if isinstance(invoice, dict) else invoice
        inv_guid = invoice.get("Guid") if isinstance(invoice, dict) else None

        rows.append([
            cn.get("CreditNoteNumber"),
            parse_unleashed_dotnet_date(cn.get("CreditNoteDate")),
            cn.get("Status"),
            cust_name,
            cust_code,
            cust_guid,
            currency_code,
            cn.get("ExchangeRate"),
            cn.get("SubTotal"),
            cn.get("TaxTotal"),
            cn.get("Total"),
            so_number,
            so_guid,
            inv_number,
            inv_guid,
            cn.get("Guid"),
            parse_unleashed_dotnet_date(cn.get("LastModifiedOn")),
        ])

    return "CreditNotes", headers, rows
