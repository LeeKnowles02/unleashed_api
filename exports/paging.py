from typing import Any, Dict, List, Optional

from exports.utils_db import try_insert_raw
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

    for page_number in range(2, number_of_pages + 1):
        page_path = f"{path.rstrip('/')}/{page_number}"
        page_data = client.get(page_path)
        pages.append(page_data)
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

    return pages
