from typing import Any, Dict, List, Tuple, Optional
from unleashed_client import UnleashedClient
from exports.paging import fetch_all_pages
from exports.utils import parse_unleashed_dotnet_date

ExportResult = Tuple[str, List[str], List[List[Any]]]


def dummy() -> ExportResult:
    return "Products", ["ProductCode", "ProductDescription", "Guid"], [
        ["P001", "Espresso Beans", "00000000-0000-0000-0000-000000000001"],
        ["P002", "Milk Powder", "00000000-0000-0000-0000-000000000002"],
    ]


def from_api(client: UnleashedClient, *, run_id: Optional[str] = None, company_id: Optional[str] = None) -> ExportResult:
    pages = fetch_all_pages(
        client,
        "/Products",
        endpoint="Products",
        run_id=run_id,
        company_id=company_id,
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

    for data in pages:
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
