from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date
from exports.utils_db import try_insert_raw

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return (
        "Customers",
        ["CustomerCode", "CustomerName", "Email"],
        [
            ["CUST001", "Cafe Nero", "accounts@cafenero.com"],
            ["CUST002", "Coffee Corner", "admin@coffeecorner.com"],
        ],
    )


def _as_name(value: Any, name_key: str) -> Any:
    """
    If value is a dict, return value[name_key]. If it's already a string, return it.
    Otherwise return None.
    """
    if isinstance(value, dict):
        return value.get(name_key)
    if isinstance(value, str):
        return value
    return None


def _as_code(value: Any, code_key: str) -> Any:
    if isinstance(value, dict):
        return value.get(code_key)
    if isinstance(value, str):
        return value
    return None


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    data: Dict[str, Any] = client.get("/Customers")
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint="Customers",
        http_status=getattr(client, "last_status_code", None),
        payload_obj=data,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
    )
    headers = [
        "CustomerCode",
        "CustomerName",
        "CustomerType",
        "Email",
        "PhoneNumber",
        "MobileNumber",
        "Website",
        "CustomerRef",
        "DiscountRate",
        "Taxable",
        "Currency",
        "Guid",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for c in data.get("Items", []):
        customer_type = _as_name(c.get("CustomerType"), "CustomerTypeName")
        currency = _as_code(c.get("Currency"), "CurrencyCode")

        rows.append(
            [
                c.get("CustomerCode"),
                c.get("CustomerName"),
                customer_type,
                c.get("Email"),
                c.get("PhoneNumber"),
                c.get("MobileNumber"),
                c.get("Website"),
                c.get("CustomerRef"),
                c.get("DiscountRate"),
                c.get("Taxable"),
                currency,
                c.get("Guid"),
                parse_unleashed_dotnet_date(c.get("LastModifiedOn")),
            ]
        )

    return "Customers", headers, rows
