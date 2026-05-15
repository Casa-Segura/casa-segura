from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from shared.domain.entities.annotations import Annotation
from shared.domain.entities.pagination import QuerySet, QuerySetPagination
from shared.domain.entities.specifications import Specification

T = TypeVar("T")


class ReadOnlyRepository(ABC, Generic[T]):
    """Interface for read operations."""

    @abstractmethod
    def get(
        self,
        criteria: List[Specification],
        annotations: Optional[List[Annotation]] = None,
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    def find(
        self,
        criteria: List[Specification],
        annotations: Optional[List[Annotation]] = None,
    ) -> Optional[T]:
        raise NotImplementedError()

    @abstractmethod
    def filter(
        self,
        criteria: List[Specification],
        pagination: Optional[QuerySetPagination] = None,
        order_by: Optional[List[str]] = None,
        annotations: Optional[List[Annotation]] = None,
        distinct: bool = False,
    ) -> QuerySet[T]:
        raise NotImplementedError()

    @abstractmethod
    def all(self) -> QuerySet[T]:
        raise NotImplementedError()


class WriteOnlyRepository(ABC, Generic[T]):
    """Interface for write operations."""

    @abstractmethod
    def save(self, entity: T) -> T:
        raise NotImplementedError()

    @abstractmethod
    def delete(self, entity: T) -> None:
        raise NotImplementedError()

    @abstractmethod
    def bulk_create(self, entities: List[T]) -> List[T]:
        raise NotImplementedError()

    @abstractmethod
    def bulk_update(self, entities: List[T], *, fields: List[str]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def bulk_delete(self, entities: List[T]) -> None:
        raise NotImplementedError()


class BaseRepository(ReadOnlyRepository[T], WriteOnlyRepository[T], Generic[T]):
    """Full repository combining read and write interfaces."""

    pass
