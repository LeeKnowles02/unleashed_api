import time
from typing import Any, Dict, List, Tuple, Optional

from unleashed_client import UnleashedClient
from exports.paging import fetch_all_pages
from exports.utils import parse_unleashed_dotnet_date
from integration_log_writer import log_error, log_info

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
    n_pages = len(pages)
    log_info(
        f"Transformation started: Products — mapping {n_pages} API page payload(s) to flat Excel/SQL rows "
        f"(nested ProductGroup, UnitOfMeasure flattened; run_id={run_id!r}).",
        integration_name="unleashed_api",
        module_name="exports.products",
        function_name="from_api",
        event_type="transformation_started",
        action="map_api_to_rows",
        entity_name="Products",
        endpoint="/Products",
        status="STARTED",
        record_count=n_pages,
        detail="Iterates Items per page; datetime fields parsed via parse_unleashed_dotnet_date.",
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
    t0 = time.perf_counter()

    try:
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
    except Exception as exc:
        log_error(
            f"Transformation failed: Products — error while flattening Items to rows after {int((time.perf_counter() - t0) * 1000)} ms.",
            exc=exc,
            integration_name="unleashed_api",
            module_name="exports.products",
            function_name="from_api",
            event_type="transformation_failed",
            action="map_api_to_rows",
            entity_name="Products",
            endpoint="/Products",
            status="FAIL",
            detail="Inspect source payload shape for unexpected nulls or types; compare to Unleashed Products schema.",
        )
        raise

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    log_info(
        f"Transformation completed: Products — produced {len(rows)} row(s) from {n_pages} page(s) in {elapsed_ms} ms.",
        integration_name="unleashed_api",
        module_name="exports.products",
        function_name="from_api",
        event_type="transformation_completed",
        action="map_api_to_rows",
        entity_name="Products",
        endpoint="/Products",
        status="SUCCESS",
        record_count=len(rows),
        duration_ms=elapsed_ms,
    )

    return "Products", headers, rows
