from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from django.db.models import Model

from shared.domain.entities.specifications import Specification


class Annotation(BaseModel, ABC):
    """Abstract base class for Django ORM annotations."""

    field: str
    alias: str
    output_field: Any | None = None

    model_config = {"arbitrary_types_allowed": True}

    @abstractmethod
    def get_annotation(self) -> dict:
        raise NotImplementedError()


class CountAnnotation(Annotation):
    distinct: bool = False
    filter_spec: Specification | None = None

    def get_annotation(self) -> dict:
        from django.db.models import Count

        kwargs: dict = {}
        if self.distinct:
            kwargs["distinct"] = True
        if self.output_field:
            kwargs["output_field"] = self.output_field
        if self.filter_spec:
            kwargs["filter"] = self.filter_spec.to_q()
        return {self.alias: Count(self.field, **kwargs)}


class SumAnnotation(Annotation):
    filter_spec: Specification | None = None

    def get_annotation(self) -> dict:
        from django.db.models import Sum

        kwargs: dict = {}
        if self.output_field:
            kwargs["output_field"] = self.output_field
        if self.filter_spec:
            kwargs["filter"] = self.filter_spec.to_q()
        return {self.alias: Sum(self.field, **kwargs)}


class AvgAnnotation(Annotation):
    filter_spec: Specification | None = None

    def get_annotation(self) -> dict:
        from django.db.models import Avg

        kwargs: dict = {}
        if self.output_field:
            kwargs["output_field"] = self.output_field
        if self.filter_spec:
            kwargs["filter"] = self.filter_spec.to_q()
        return {self.alias: Avg(self.field, **kwargs)}


class MaxAnnotation(Annotation):
    def get_annotation(self) -> dict:
        from django.db.models import Max

        kwargs: dict = {}
        if self.output_field:
            kwargs["output_field"] = self.output_field
        return {self.alias: Max(self.field, **kwargs)}


class MinAnnotation(Annotation):
    def get_annotation(self) -> dict:
        from django.db.models import Min

        kwargs: dict = {}
        if self.output_field:
            kwargs["output_field"] = self.output_field
        return {self.alias: Min(self.field, **kwargs)}


class ExistsAnnotation(Annotation):
    related_model: str | None = None
    filter_spec: Specification | None = None

    def get_annotation(self) -> dict:
        return {
            self.alias: {
                "_type": "exists",
                "field": self.field,
                "filter_spec": self.filter_spec,
            }
        }


class ExpressionAnnotation(Annotation):
    expression: str

    def get_annotation(self) -> dict:
        from django.db.models import F

        return {self.alias: F(self.field)}


class CaseAnnotation(Annotation):
    cases: list[tuple]
    default: Any = None

    def get_annotation(self) -> dict:
        from django.db.models import Case, CharField, Value, When

        whens = [When(spec.to_q(), then=Value(value)) for spec, value in self.cases]
        kwargs: dict = {"output_field": self.output_field or CharField()}
        if self.default is not None:
            kwargs["default"] = Value(self.default)
        return {self.alias: Case(*whens, **kwargs)}


class SubqueryAnnotation(Annotation):
    subquery_field: str
    filter_spec: Specification | None = None
    order_by: list[str] | None = None

    def get_annotation(self) -> dict:
        return {
            self.alias: {
                "_type": "subquery",
                "field": self.field,
                "subquery_field": self.subquery_field,
                "filter_spec": self.filter_spec,
                "order_by": self.order_by,
            }
        }


class JsonArrayLengthAnnotation(Annotation):
    def get_annotation(self) -> dict:
        from django.db.models import F, Func, IntegerField

        output = self.output_field or IntegerField()
        return {
            self.alias: Func(
                F(self.field),
                function="jsonb_array_length",
                output_field=output,
            )
        }


class RelatedItemsCountAnnotation(Annotation):
    def get_annotation(self) -> dict:
        from django.db.models import Count, IntegerField

        return {self.alias: Count(self.field, output_field=self.output_field or IntegerField())}


class RawAnnotation(Annotation):
    raw_expression: Any

    def get_annotation(self) -> dict:
        return {self.alias: self.raw_expression}


class DjangoORMAnnotationBuilder:
    """Builder that converts domain annotations to Django ORM annotations."""

    def build(self, annotations: list[Annotation] | None) -> dict:
        if not annotations:
            return {}
        result: dict = {}
        for annotation in annotations:
            result.update(annotation.get_annotation())
        return result

    def build_with_model(self, annotations: list[Annotation] | None, model: type[Model]) -> dict:
        from django.db.models import Exists, OuterRef, Subquery

        if not annotations:
            return {}
        result: dict = {}
        for annotation in annotations:
            annotation_dict = annotation.get_annotation()
            for alias, value in annotation_dict.items():
                if isinstance(value, dict) and value.get("_type") == "exists":
                    related_name = value["field"]
                    filter_spec = value.get("filter_spec")
                    related_field = model._meta.get_field(related_name)
                    related_model = related_field.related_model
                    subquery = related_model.objects.filter(**{f"{related_field.field.name}": OuterRef("pk")})
                    if filter_spec:
                        subquery = subquery.filter(filter_spec.to_q())
                    result[alias] = Exists(subquery)
                elif isinstance(value, dict) and value.get("_type") == "subquery":
                    related_name = value["field"]
                    subquery_field = value["subquery_field"]
                    filter_spec = value.get("filter_spec")
                    order_by = value.get("order_by", [])
                    related_field = model._meta.get_field(related_name)
                    related_model = related_field.related_model
                    subquery = related_model.objects.filter(**{f"{related_field.field.name}": OuterRef("pk")})
                    if filter_spec:
                        subquery = subquery.filter(filter_spec.to_q())
                    if order_by:
                        subquery = subquery.order_by(*order_by)
                    subquery = subquery.values(subquery_field)[:1]
                    result[alias] = Subquery(subquery)
                else:
                    result[alias] = value
        return result
