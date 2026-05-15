from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class QuerySetPagination(BaseModel):
    """Pagination parameters."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page_size * self.page) - self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def array_slice(self) -> slice:
        return slice(self.offset, self.offset + self.limit)


class QuerySet(Generic[T]):
    """Generic wrapper for query results."""

    def __init__(self, *, data: List[T], count: Optional[int] = None) -> None:
        self._data: List[T] = data
        self._count: Optional[int] = count

    @property
    def data(self) -> List[T]:
        return self._data

    @property
    def count(self) -> int:
        return self._count if self._count is not None else len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def first(self) -> Optional[T]:
        return self.data[0] if self.data else None

    def last(self) -> Optional[T]:
        return self.data[-1] if self.data else None

    def sort(self, *args, **kwargs) -> None:
        self._data.sort(*args, **kwargs)


class PaginationData(BaseModel):
    """Pagination metadata for API responses."""

    previous_page: Optional[str] = Field(None, alias="previousPage")
    next_page: Optional[str] = Field(None, alias="nextPage")
    current_page: int = Field(..., alias="currentPage")
    total_pages: int = Field(..., alias="totalPages")
    total_items_on_page: int = Field(..., alias="totalItemsOnPage")
    total_items: int = Field(..., alias="totalItems")
    page_size: int = Field(..., alias="pageSize")


class PaginatedQuerySet(BaseModel, Generic[T]):
    """Paginated result with metadata for APIs."""

    pagination_data: PaginationData
    query_params: dict = Field(default_factory=dict)
    results: List[T]
