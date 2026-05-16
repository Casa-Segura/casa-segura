from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from shared.domain.entities.annotations import Annotation
from shared.domain.entities.pagination import QuerySet, QuerySetPagination
from shared.domain.entities.specifications import Specification

T = TypeVar("T")


class ReadOnlyRepository(ABC, Generic[T]):
    """Interface for read operations."""

    @abstractmethod
    def get(
        self,
        criteria: list[Specification],
        annotations: list[Annotation] | None = None,
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    def find(
        self,
        criteria: list[Specification],
        annotations: list[Annotation] | None = None,
    ) -> T | None:
        raise NotImplementedError()

    @abstractmethod
    def filter(
        self,
        criteria: list[Specification],
        pagination: QuerySetPagination | None = None,
        order_by: list[str] | None = None,
        annotations: list[Annotation] | None = None,
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
    def bulk_create(self, entities: list[T]) -> list[T]:
        raise NotImplementedError()

    @abstractmethod
    def bulk_update(self, entities: list[T], *, fields: list[str]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def bulk_delete(self, entities: list[T]) -> None:
        raise NotImplementedError()


class BaseRepository(ReadOnlyRepository[T], WriteOnlyRepository[T], Generic[T]):
    """Full repository combining read and write interfaces."""

    pass
