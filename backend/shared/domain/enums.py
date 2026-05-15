from __future__ import annotations

from enum import IntEnum


class CriteriaOperator(IntEnum):
    """Comparison operators available for specifications. Map directly to Django ORM lookups."""

    EQUAL = 0
    NOT_EQUAL = 1
    IN = 2
    NOT_IN = 3
    LTE = 4
    LT = 5
    GTE = 6
    GT = 7
    ICONTAINS = 8
    CONTAINS = 9
    EXACT = 10
    IEXACT = 11
    STARTSWITH = 12
    ISTARTSWITH = 13
    ENDSWITH = 14
    IENDSWITH = 15
    RANGE = 16
    IS_NULL = 17
    REGEX = 18
    IREGEX = 19


class LogicalOperator(IntEnum):
    """Logical operators for combining specifications."""

    AND = 0
    OR = 1


EQ = CriteriaOperator.EQUAL
NE = CriteriaOperator.NOT_EQUAL
IN = CriteriaOperator.IN
NIN = CriteriaOperator.NOT_IN
GT = CriteriaOperator.GT
GTE = CriteriaOperator.GTE
LT = CriteriaOperator.LT
LTE = CriteriaOperator.LTE
LIKE = CriteriaOperator.ICONTAINS
CONTAINS = CriteriaOperator.CONTAINS
NULL = CriteriaOperator.IS_NULL
RANGE = CriteriaOperator.RANGE
STARTSWITH = CriteriaOperator.STARTSWITH
ENDSWITH = CriteriaOperator.ENDSWITH
