from typing import Any, Dict, List, Tuple
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "Suppliers", ["SupplierCode", "SupplierName", "Email"], [
        ["SUP001", "Bean Importers Ltd", "orders@beanimporters.com"],
        ["SUP002", "Packaging Co", "sales@packagingco.com"],
    ]


def from_api(client: UnleashedClient) -> ExportResult:
    data: Dict[str, Any] = client.get("/Suppliers")

    headers = [
        "SupplierCode",
        "SupplierName",
        "Email",
        "PhoneNumber",
        "MobileNumber",
        "Website",
        "SupplierRef",
        "Currency",
        "Guid",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for s in data.get("Items", []):
        currency = s.get("Currency")
        currency_code = currency.get("CurrencyCode") if isinstance(currency, dict) else currency

        rows.append([
            s.get("SupplierCode"),
            s.get("SupplierName"),
            s.get("Email"),
            s.get("PhoneNumber"),
            s.get("MobileNumber"),
            s.get("Website"),
            s.get("SupplierRef"),
            currency_code,
            s.get("Guid"),
            parse_unleashed_dotnet_date(s.get("LastModifiedOn")),
        ])

    return "Suppliers", headers, rows
