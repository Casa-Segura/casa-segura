import math
from urllib import parse

from shared.domain.entities.pagination import PaginatedQuerySet, PaginationData, QuerySet


def paginate_queryset(*, queryset: QuerySet, page: int, page_size: int, url: str) -> dict:
    """Generate a paginated response with navigation URLs."""

    def _replace_query_param(url: str, query_param: str, query_value: str) -> str:
        parsed_url = parse.urlparse(url)
        query_params = parse.parse_qs(parsed_url.query)
        query_params[query_param] = [query_value]
        new_query = parse.urlencode(query_params, doseq=True)
        return parse.urlunparse(parsed_url._replace(query=new_query))

    total_pages = math.ceil(queryset.count / page_size) if page_size > 0 else 0

    return PaginatedQuerySet(
        pagination_data=PaginationData(
            previousPage=_replace_query_param(url, "page", str(page - 1)) if page > 1 else None,
            nextPage=_replace_query_param(url, "page", str(page + 1)) if page < total_pages else None,
            currentPage=page,
            totalPages=total_pages,
            totalItemsOnPage=min(len(queryset.data), page_size),
            totalItems=queryset.count,
            pageSize=page_size,
        ),
        results=queryset.data,
    ).model_dump()
