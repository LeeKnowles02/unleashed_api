from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.utils import parse_unleashed_dotnet_date
from exports.utils_db import try_insert_raw

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "Products", ["ProductCode", "ProductDescription", "Guid"], [
        ["P001", "Espresso Beans", "00000000-0000-0000-0000-000000000001"],
        ["P002", "Milk Powder", "00000000-0000-0000-0000-000000000002"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    data: Dict[str, Any] = client.get("/Products")
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint="Products",
        http_status=getattr(client, "last_status_code", None),
        payload_obj=data,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
    )
    headers = [
        "ProductCode",
        "ProductDescription",
        "Barcode",
        "IsObsolete",
        "IsComponent",
        "DefaultPurchasePrice",
        "DefaultSellPrice",
        "AverageLandCost",
        "ProductGroup",
        "UnitOfMeasure",
        "Guid",
        "LastModifiedOn",
    ]

    rows: List[List[Any]] = []

    for p in data.get("Items", []):
        group = p.get("ProductGroup")
        group_name = group.get("GroupName") if isinstance(group, dict) else group

        uom = p.get("UnitOfMeasure")
        uom_name = uom.get("Name") if isinstance(uom, dict) else uom

        rows.append([
            p.get("ProductCode"),
            p.get("ProductDescription"),
            p.get("Barcode"),
            p.get("IsObsolete"),
            p.get("IsComponent"),
            p.get("DefaultPurchasePrice"),
            p.get("DefaultSellPrice"),
            p.get("AverageLandCost"),
            group_name,
            uom_name,
            p.get("Guid"),
            parse_unleashed_dotnet_date(p.get("LastModifiedOn")),
        ])

    return "Products", headers, rows
