from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.paging import fetch_all_pages
from exports.utils import parse_unleashed_dotnet_date

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "Warehouses", ["WarehouseCode", "WarehouseName", "Guid"], [
        ["MAIN", "Main Warehouse", "00000000-0000-0000-0000-000000000001"],
        ["CPT", "Cape Town", "00000000-0000-0000-0000-000000000002"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    pages = fetch_all_pages(
        client,
        "/Warehouses",
        endpoint="Warehouses",
        run_id=run_id,
        company_id=company_id,
    )
    headers = [
        "WarehouseCode",
        "WarehouseName",
        "IsDefault",
        "IsObsolete",
        "StreetAddress",
        "Suburb",
        "City",
        "Region",
        "Country",
        "PostCode",
        "Guid",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for data in pages:
        for w in data.get("Items", []):
            address = w.get("Address")
            if not isinstance(address, dict):
                address = {}

            rows.append([
                w.get("WarehouseCode"),
                w.get("WarehouseName"),
                w.get("IsDefault"),
                w.get("IsObsolete"),
                address.get("StreetAddress"),
                address.get("Suburb"),
                address.get("City"),
                address.get("Region"),
                address.get("Country"),
                address.get("PostCode"),
                w.get("Guid"),
                parse_unleashed_dotnet_date(w.get("LastModifiedOn")),
            ])

    return "Warehouses", headers, rows
