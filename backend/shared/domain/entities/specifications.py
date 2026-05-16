from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel

from django.db.models import Q

from shared.domain.enums import CriteriaOperator, LogicalOperator


class Specification(ABC):
    """Abstract base class for all search specifications."""

    @abstractmethod
    def to_q(self) -> Q:
        raise NotImplementedError()

    def __and__(self, other: Specification) -> CompositeSpec:
        return CompositeSpec([self, other], LogicalOperator.AND)

    def __or__(self, other: Specification) -> CompositeSpec:
        return CompositeSpec([self, other], LogicalOperator.OR)

    def __invert__(self) -> NotSpec:
        return NotSpec(self)


class FieldSpec(Specification):
    """Specification for conditions on a single field."""

    OPERATOR_LOOKUP_MAP: ClassVar = {
        CriteriaOperator.EQUAL: "",
        CriteriaOperator.NOT_EQUAL: "",
        CriteriaOperator.IN: "__in",
        CriteriaOperator.NOT_IN: "__in",
        CriteriaOperator.LTE: "__lte",
        CriteriaOperator.LT: "__lt",
        CriteriaOperator.GTE: "__gte",
        CriteriaOperator.GT: "__gt",
        CriteriaOperator.ICONTAINS: "__icontains",
        CriteriaOperator.CONTAINS: "__contains",
        CriteriaOperator.EXACT: "__exact",
        CriteriaOperator.IEXACT: "__iexact",
        CriteriaOperator.STARTSWITH: "__startswith",
        CriteriaOperator.ISTARTSWITH: "__istartswith",
        CriteriaOperator.ENDSWITH: "__endswith",
        CriteriaOperator.IENDSWITH: "__iendswith",
        CriteriaOperator.RANGE: "__range",
        CriteriaOperator.IS_NULL: "__isnull",
        CriteriaOperator.REGEX: "__regex",
        CriteriaOperator.IREGEX: "__iregex",
    }

    NEGATED_OPERATORS: ClassVar = {CriteriaOperator.NOT_EQUAL, CriteriaOperator.NOT_IN}

    def __init__(self, field: str, operator: CriteriaOperator, value: Any, negate: bool = False):
        self.field = field
        self.operator = operator
        self.value = value
        self.negate = negate

    def to_q(self) -> Q:
        lookup = self.OPERATOR_LOOKUP_MAP.get(self.operator, "")
        field_lookup = f"{self.field}{lookup}"
        q = Q(**{field_lookup: self.value})
        should_negate = self.negate or (self.operator in self.NEGATED_OPERATORS)
        return ~q if should_negate else q

    def __repr__(self) -> str:
        neg = "NOT " if self.negate or self.operator in self.NEGATED_OPERATORS else ""
        return f"{neg}FieldSpec({self.field}, {self.operator.name}, {self.value!r})"


class CompositeSpec(Specification):
    """Combines multiple specifications with AND or OR."""

    def __init__(self, specs: list[Specification], operator: LogicalOperator = LogicalOperator.AND):
        self.specs = specs
        self.operator = operator

    def to_q(self) -> Q:
        if not self.specs:
            return Q()
        result = self.specs[0].to_q()
        for spec in self.specs[1:]:
            if self.operator == LogicalOperator.AND:
                result = result & spec.to_q()
            else:
                result = result | spec.to_q()
        return result

    def __repr__(self) -> str:
        op = " AND " if self.operator == LogicalOperator.AND else " OR "
        return f"({op.join(repr(s) for s in self.specs)})"


class NotSpec(Specification):
    """Negates a specification."""

    def __init__(self, spec: Specification):
        self.spec = spec

    def to_q(self) -> Q:
        return ~self.spec.to_q()

    def __repr__(self) -> str:
        return f"NOT({self.spec!r})"


class RelatedFieldSpec(Specification):
    """Specification for fields on related models."""

    def __init__(
        self,
        relation_path: list[str],
        field: str,
        operator: CriteriaOperator,
        value: Any,
        negate: bool = False,
    ):
        self.relation_path = relation_path
        self.field = field
        self.operator = operator
        self.value = value
        self.negate = negate

    @property
    def full_field(self) -> str:
        return "__".join([*self.relation_path, self.field])

    def to_q(self) -> Q:
        return FieldSpec(self.full_field, self.operator, self.value, self.negate).to_q()

    def __repr__(self) -> str:
        neg = "NOT " if self.negate else ""
        path = ".".join(self.relation_path)
        return f"{neg}RelatedFieldSpec({path}.{self.field}, {self.operator.name}, {self.value!r})"


class RawQSpec(Specification):
    """Passes a Q object directly (escape hatch)."""

    def __init__(self, q: Q):
        self._q = q

    def to_q(self) -> Q:
        return self._q

    def __repr__(self) -> str:
        return f"RawQSpec({self._q})"


class LegacySpecification(BaseModel):
    """Legacy Pydantic-based specification, kept for backward compatibility."""

    field: str
    value: Any
    operator: CriteriaOperator = CriteriaOperator.EQUAL

    model_config = {"arbitrary_types_allowed": True}


class LegacySpecificationAdapter(Specification):
    """Adapts LegacySpecification (Pydantic) to the new Q-based system."""

    def __init__(self, legacy_spec: LegacySpecification):
        self.legacy = legacy_spec

    def to_q(self) -> Q:
        return FieldSpec(
            field=self.legacy.field,
            operator=self.legacy.operator,
            value=self.legacy.value,
        ).to_q()

    def __repr__(self) -> str:
        return f"LegacyAdapter({self.legacy.field}, {self.legacy.operator.name}, {self.legacy.value!r})"


class FieldBuilder:
    """Auxiliary builder for fluent FieldSpec construction."""

    def __init__(self, parent: SpecBuilder, field: str):
        self._parent = parent
        self._field = field

    def equals(self, value: Any) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.EQUAL, value))
        return self._parent

    def not_equals(self, value: Any) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.NOT_EQUAL, value))
        return self._parent

    def is_in(self, values: list[Any]) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.IN, values))
        return self._parent

    def not_in(self, values: list[Any]) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.NOT_IN, values))
        return self._parent

    def gt(self, value: Any) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.GT, value))
        return self._parent

    def gte(self, value: Any) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.GTE, value))
        return self._parent

    def lt(self, value: Any) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.LT, value))
        return self._parent

    def lte(self, value: Any) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.LTE, value))
        return self._parent

    def contains(self, value: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.CONTAINS, value))
        return self._parent

    def icontains(self, value: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.ICONTAINS, value))
        return self._parent

    def startswith(self, value: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.STARTSWITH, value))
        return self._parent

    def istartswith(self, value: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.ISTARTSWITH, value))
        return self._parent

    def endswith(self, value: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.ENDSWITH, value))
        return self._parent

    def iendswith(self, value: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.IENDSWITH, value))
        return self._parent

    def between(self, start: Any, end: Any) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.RANGE, (start, end)))
        return self._parent

    def is_null(self) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.IS_NULL, True))
        return self._parent

    def is_not_null(self) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.IS_NULL, False))
        return self._parent

    def matches(self, pattern: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.REGEX, pattern))
        return self._parent

    def imatches(self, pattern: str) -> SpecBuilder:
        self._parent._specs.append(FieldSpec(self._field, CriteriaOperator.IREGEX, pattern))
        return self._parent


class SpecBuilder:
    """Fluent builder for constructing specifications in a readable way."""

    def __init__(self):
        self._specs: list[Specification] = []

    def where(self, field: str) -> FieldBuilder:
        return FieldBuilder(self, field)

    def and_group(self, *specs: Specification) -> SpecBuilder:
        self._specs.append(CompositeSpec(list(specs), LogicalOperator.AND))
        return self

    def or_group(self, *specs: Specification) -> SpecBuilder:
        self._specs.append(CompositeSpec(list(specs), LogicalOperator.OR))
        return self

    def not_spec(self, spec: Specification) -> SpecBuilder:
        self._specs.append(NotSpec(spec))
        return self

    def add(self, spec: Specification) -> SpecBuilder:
        self._specs.append(spec)
        return self

    def build(self) -> list[Specification]:
        return self._specs

    def to_q(self) -> Q:
        return CompositeSpec(self._specs, LogicalOperator.AND).to_q()


def and_(*specs: Specification) -> CompositeSpec:
    return CompositeSpec(list(specs), LogicalOperator.AND)


def or_(*specs: Specification) -> CompositeSpec:
    return CompositeSpec(list(specs), LogicalOperator.OR)


def not_(spec: Specification) -> NotSpec:
    return NotSpec(spec)


class DjangoORMSpecificationBuilder:
    """Builder that converts specifications to Django Q objects."""

    def build(self, criteria: list[Specification]) -> Q:
        if not criteria:
            return Q()
        return CompositeSpec(criteria, LogicalOperator.AND).to_q()

    def build_or(self, criteria: list[Specification]) -> Q:
        if not criteria:
            return Q()
        return CompositeSpec(criteria, LogicalOperator.OR).to_q()

    def build_from_legacy(self, legacy_specs: list[LegacySpecification]) -> Q:
        adapted: list[Specification] = [LegacySpecificationAdapter(s) for s in legacy_specs]
        return self.build(adapted)
