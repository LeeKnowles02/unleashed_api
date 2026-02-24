from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date
from exports.utils_db import try_insert_raw

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "Warehouses", ["WarehouseCode", "WarehouseName", "Guid"], [
        ["MAIN", "Main Warehouse", "00000000-0000-0000-0000-000000000001"],
        ["CPT", "Cape Town", "00000000-0000-0000-0000-000000000002"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    data: Dict[str, Any] = client.get("/Warehouses")
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint="Warehouses",
        http_status=getattr(client, "last_status_code", None),
        payload_obj=data,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
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
