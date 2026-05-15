from __future__ import annotations

from abc import abstractmethod
from contextlib import contextmanager
from typing import Generic, List, Optional, Type, TypeVar

from django.db import transaction
from django.db.models import F, Model, OrderBy
from django.db.models import QuerySet as DjangoQuerySet

from shared.domain.entities.annotations import Annotation, DjangoORMAnnotationBuilder
from shared.domain.entities.pagination import QuerySet, QuerySetPagination
from shared.domain.entities.repositories import ReadOnlyRepository, WriteOnlyRepository
from shared.domain.entities.specifications import (
    CompositeSpec,
    DjangoORMSpecificationBuilder,
    FieldSpec,
    Specification,
)

T = TypeVar("T")
K = TypeVar("K", bound=Model)


class EntityNotFoundError(Exception):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, criteria: dict):
        self.entity_type = entity_type
        self.criteria = criteria
        super().__init__(f"{entity_type} not found with criteria: {criteria}")


class MultipleEntitiesFoundError(Exception):
    """Raised when one entity was expected but multiple were found."""

    def __init__(self, entity_type: str, count: int):
        self.entity_type = entity_type
        self.count = count
        super().__init__(f"Expected 1 {entity_type}, found {count}")


class DjangoReadRepository(Generic[T, K], ReadOnlyRepository[T]):
    """Read repository implementation for Django ORM."""

    __model__: Type[K]

    def __init__(self):
        self.spec_builder = DjangoORMSpecificationBuilder()
        self.annotation_builder = DjangoORMAnnotationBuilder()

    @abstractmethod
    def to_entity(self, model: K) -> T:
        raise NotImplementedError()

    def _optimize_queryset(self, queryset: DjangoQuerySet) -> DjangoQuerySet:
        return queryset

    def get(
        self,
        criteria: List[Specification],
        annotations: Optional[List[Annotation]] = None,
    ) -> T:
        q = self.spec_builder.build(criteria)
        queryset = self._optimize_queryset(self.__model__.objects.filter(q))

        if annotations:
            annotation_dict = self.annotation_builder.build_with_model(annotations, self.__model__)
            queryset = queryset.annotate(**annotation_dict)

        try:
            return self.to_entity(queryset.get())
        except self.__model__.DoesNotExist:
            raise EntityNotFoundError(self.__model__.__name__, {str(c): True for c in criteria})
        except self.__model__.MultipleObjectsReturned:
            raise MultipleEntitiesFoundError(self.__model__.__name__, queryset.count())

    def find(
        self,
        criteria: List[Specification],
        annotations: Optional[List[Annotation]] = None,
    ) -> Optional[T]:
        q = self.spec_builder.build(criteria)
        queryset = self._optimize_queryset(self.__model__.objects.filter(q))

        if annotations:
            annotation_dict = self.annotation_builder.build_with_model(annotations, self.__model__)
            queryset = queryset.annotate(**annotation_dict)

        try:
            return self.to_entity(queryset.get())
        except self.__model__.DoesNotExist:
            return None

    def filter(
        self,
        criteria: List[Specification],
        pagination: Optional[QuerySetPagination] = None,
        order_by: Optional[List[str]] = None,
        annotations: Optional[List[Annotation]] = None,
        distinct: bool = False,
    ) -> QuerySet[T]:
        annotated_fields = [ann.alias for ann in annotations] if annotations else []

        regular_criteria = [s for s in criteria if not self._is_annotated_field(s, annotated_fields)]
        annotated_criteria = [s for s in criteria if self._is_annotated_field(s, annotated_fields)]

        q = self.spec_builder.build(regular_criteria)
        queryset = self._optimize_queryset(self.__model__.objects.filter(q))

        if annotations:
            annotation_dict = self.annotation_builder.build_with_model(annotations, self.__model__)
            queryset = queryset.annotate(**annotation_dict)

        if annotated_criteria:
            annotated_q = self.spec_builder.build(annotated_criteria)
            queryset = queryset.filter(annotated_q)

        if distinct:
            queryset = queryset.distinct()

        if order_by:
            processed_order_by: List[OrderBy] = [
                F(field.lstrip("-")).desc(nulls_last=True)
                if field.startswith("-")
                else F(field).asc(nulls_last=True)
                for field in order_by
            ]
            queryset = queryset.order_by(*processed_order_by)

        count = queryset.count()

        if pagination:
            queryset = queryset[pagination.array_slice]

        entities = [self.to_entity(obj) for obj in queryset]
        return QuerySet(data=entities, count=count)

    def _is_annotated_field(self, spec: Specification, annotated_fields: List[str]) -> bool:
        if isinstance(spec, FieldSpec):
            return spec.field in annotated_fields
        elif isinstance(spec, CompositeSpec):
            return any(self._is_annotated_field(s, annotated_fields) for s in spec.specs)
        return False

    def all(self) -> QuerySet[T]:
        queryset = self._optimize_queryset(self.__model__.objects.all())
        entities = [self.to_entity(obj) for obj in queryset]
        return QuerySet(data=entities)

    def count(self, criteria: Optional[List[Specification]] = None) -> int:
        if criteria:
            q = self.spec_builder.build(criteria)
            return self.__model__.objects.filter(q).count()
        return self.__model__.objects.count()

    def exists(self, criteria: List[Specification]) -> bool:
        q = self.spec_builder.build(criteria)
        return self.__model__.objects.filter(q).exists()

    def aggregate(
        self,
        criteria: Optional[List[Specification]] = None,
        annotations: Optional[List[Annotation]] = None,
    ) -> dict:
        queryset = self.__model__.objects.all()
        if criteria:
            q = self.spec_builder.build(criteria)
            queryset = queryset.filter(q)
        if not annotations:
            return {}
        annotation_dict = self.annotation_builder.build(annotations)
        return queryset.aggregate(**annotation_dict)


class DjangoWriteRepository(Generic[T, K], WriteOnlyRepository[T]):
    """Write repository implementation for Django ORM."""

    __model__: Type[K]

    @abstractmethod
    def to_entity(self, model: K) -> T:
        raise NotImplementedError()

    @abstractmethod
    def to_orm_model(self, entity: T) -> K:
        raise NotImplementedError()

    def save(self, entity: T) -> T:
        model = self.to_orm_model(entity)
        model.save()
        return self.to_entity(model)

    def delete(self, entity: T) -> None:
        model = self.to_orm_model(entity)
        model.delete()

    def bulk_create(self, entities: List[T]) -> List[T]:
        models = [self.to_orm_model(e) for e in entities]
        created = self.__model__.objects.bulk_create(models)
        return [self.to_entity(m) for m in created]

    def bulk_update(self, entities: List[T], *, fields: List[str]) -> None:
        models = [self.to_orm_model(e) for e in entities]
        self.__model__.objects.bulk_update(models, fields)

    def bulk_delete(self, entities: List[T]) -> None:
        ids = [getattr(e, "id") for e in entities if getattr(e, "id", None)]
        if ids:
            self.__model__.objects.filter(id__in=ids).delete()


class DjangoFullRepository(
    DjangoReadRepository[T, K],
    DjangoWriteRepository[T, K],
    Generic[T, K],
):
    """Full repository combining read and write operations."""

    __model__: Type[K]

    @contextmanager
    def atomic(self):
        with transaction.atomic():
            yield self

    def save_all(self, entities: List[T]) -> List[T]:
        with self.atomic():
            return [self.save(e) for e in entities]
