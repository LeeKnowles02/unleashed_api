from typing import Any, Dict, List, Optional

from exports.utils_db import try_insert_raw
from integration_log_writer import log_error, log_info
from unleashed_client import UnleashedClient


def fetch_all_pages(
    client: UnleashedClient,
    path: str,
    *,
    endpoint: str,
    run_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []

    log_info(
        f"API pagination started for endpoint '{endpoint}': initial path '{path}', run_id={run_id!r}.",
        integration_name="unleashed_api",
        module_name="exports.paging",
        function_name="fetch_all_pages",
        event_type="api_pagination_started",
        action="fetch_pages",
        step_name="page_1",
        endpoint=path,
        entity_name=endpoint,
        status="STARTED",
        detail="Unleashed uses path-based pages: /Endpoint, /Endpoint/2, ... See Pagination.NumberOfPages in first response.",
    )

    first_page = client.get(path)
    pages.append(first_page)
    try_insert_raw(
        run_id=run_id,
        company_id=company_id,
        endpoint=endpoint,
        http_status=getattr(client, "last_status_code", None),
        payload_obj=first_page,
        request_url=getattr(client, "last_url", None),
        page_number=1,
        api_cursor=None,
    )

    pagination = first_page.get("Pagination") or {}
    number_of_pages = int(pagination.get("NumberOfPages") or 1)
    first_items = first_page.get("Items") if isinstance(first_page, dict) else None
    first_count = len(first_items) if isinstance(first_items, list) else 0

    log_info(
        f"API pagination first page received for '{endpoint}': NumberOfPages={number_of_pages}, PageSize={pagination.get('PageSize')}, "
        f"NumberOfItems={pagination.get('NumberOfItems')}, items_on_page_1={first_count}.",
        integration_name="unleashed_api",
        module_name="exports.paging",
        function_name="fetch_all_pages",
        event_type="api_pagination_progress",
        action="fetch_pages",
        step_name="page_1_complete",
        endpoint=path,
        entity_name=endpoint,
        status="IN_PROGRESS",
        record_count=first_count,
        detail=f"Will request pages 2..{number_of_pages} if NumberOfPages>1.",
    )

    for page_number in range(2, number_of_pages + 1):
        page_path = f"{path.rstrip('/')}/{page_number}"
        log_info(
            f"API pagination continuing: endpoint '{endpoint}', fetching page {page_number}/{number_of_pages} via path '{page_path}'.",
            integration_name="unleashed_api",
            module_name="exports.paging",
            function_name="fetch_all_pages",
            event_type="api_pagination_continued",
            action="fetch_pages",
            step_name=f"page_{page_number}",
            endpoint=page_path,
            entity_name=endpoint,
            status="IN_PROGRESS",
        )
        try:
            page_data = client.get(page_path)
            pages.append(page_data)
        except Exception as exc:
            log_error(
                f"API pagination failed on page {page_number} for endpoint '{endpoint}' (path '{page_path}').",
                exc=exc,
                integration_name="unleashed_api",
                module_name="exports.paging",
                function_name="fetch_all_pages",
                event_type="api_pagination_failed",
                action="fetch_pages",
                endpoint=page_path,
                entity_name=endpoint,
                detail="Earlier pages are in memory only; fix error and re-run export. Check Unleashed rate limits and auth.",
            )
            raise
        try_insert_raw(
            run_id=run_id,
            company_id=company_id,
            endpoint=endpoint,
            http_status=getattr(client, "last_status_code", None),
            payload_obj=page_data,
            request_url=getattr(client, "last_url", None),
            page_number=page_number,
            api_cursor=None,
        )

    total_items = 0
    for p in pages:
        it = p.get("Items") if isinstance(p, dict) else None
        if isinstance(it, list):
            total_items += len(it)

    log_info(
        f"API pagination completed for '{endpoint}': fetched {len(pages)} page(s), aggregated Items row count={total_items} "
        f"(sum of per-page Items; may include duplicates if API overlaps — not expected for Unleashed).",
        integration_name="unleashed_api",
        module_name="exports.paging",
        function_name="fetch_all_pages",
        event_type="api_pagination_completed",
        action="fetch_pages",
        step_name="all_pages",
        endpoint=path,
        entity_name=endpoint,
        status="SUCCESS",
        record_count=total_items,
        detail="Next step: export module maps Items to flat rows for Excel/SQL.",
    )

    return pages
