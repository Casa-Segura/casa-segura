"""Rubric catalog tables — RubricVersion + Criterion.

DOMAIN_MODEL §3.3, §3.7. Schema declared by F8, owned by rubric/.
Immutable catalog: rows are INSERT-only, only `is_active` may flip (enforced
by `reject_catalog_mutation` trigger created in CS-030)."""

from __future__ import annotations

import uuid

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q

from common.infrastructure.django.models import ModelWithTimeStamps
from rubric.domain.enums import Category


class RubricVersion(ModelWithTimeStamps):
    """Semantic version of the evaluation rubric. Immutable catalog (DOMAIN §3.3)."""

    version = models.CharField(
        max_length=32,
        primary_key=True,
        help_text="Semver, e.g. 1.0.0",
    )
    released_at = models.DateTimeField(help_text="When this version was released")
    criteria_count = models.PositiveIntegerField(help_text="Total criteria in this version")
    categories = models.JSONField(help_text="Definition of categories and their global weights")
    criteria_definitions_path = models.TextField(help_text="Path to the YAML file with the criteria for this version")
    changelog = models.TextField(blank=True, default="", help_text="Summary of changes vs prior version")
    is_active = models.BooleanField(
        default=False,
        help_text="Exactly one version may be active at a time (partial unique index enforces it)",
    )

    class Meta:
        db_table = "rubric_version"
        verbose_name = "Rubric Version"
        verbose_name_plural = "Rubric Versions"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="uq_rubric_version_active_singleton",
            ),
        ]

    def __str__(self) -> str:
        return f"RubricVersion({self.version})"


class Criterion(ModelWithTimeStamps):
    """Individual rubric criterion. Immutable within a rubric version (DOMAIN §3.7).

    Same criterion `code` (e.g. A1) may legitimately exist in multiple rubric versions,
    so the natural key is composite `(code, rubric_version)`. Surrogate UUID PK keeps
    Django ORM ergonomic; uniqueness is enforced by a UniqueConstraint."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=8,
        help_text="Criterion identifier within its rubric version, e.g. A1, B2, E7",
    )
    rubric_version = models.ForeignKey(
        RubricVersion,
        on_delete=models.PROTECT,
        related_name="criteria",
        db_column="rubric_version",
        help_text="Rubric version this criterion belongs to",
    )
    category = models.CharField(
        max_length=1,
        choices=Category.choices,
        help_text="Category A..F",
    )
    title = models.CharField(max_length=200, help_text="Short title of the criterion")
    description = models.TextField(help_text="What is being assessed")
    weight_in_category = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage weight within the category (0 < w <= 100)",
    )
    applicable_types = ArrayField(
        models.CharField(max_length=16),
        help_text="Contract types this criterion applies to",
    )
    legal_anchor = ArrayField(
        models.CharField(max_length=64),
        default=list,
        blank=True,
        help_text="Law articles it is based on, e.g. ['art-1605-cc', 'art-4-ley-inquilinato']",
    )
    override_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="OverrideCode triggered when this criterion fails critically (NULL if none)",
    )
    evaluation_prompt = models.TextField(help_text="LLM prompt template for evaluating this criterion")
    scoring_scale = models.JSONField(help_text="0-10 scale definition with textual criteria per band")
    worst_case_when_unverifiable = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=4.0,
        help_text="Score contributed when the criterion is unverifiable",
    )

    class Meta:
        db_table = "criterion"
        verbose_name = "Criterion"
        verbose_name_plural = "Criteria"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "rubric_version"],
                name="uq_criterion_code_rubric",
            ),
            models.CheckConstraint(
                check=Q(weight_in_category__gt=0) & Q(weight_in_category__lte=100),
                name="ck_criterion_weight_range",
            ),
            models.CheckConstraint(
                check=Q(category__in=[c.value for c in Category]),
                name="ck_criterion_category_enum",
            ),
        ]
        indexes = [
            models.Index(fields=["rubric_version"], name="idx_criterion_rubric"),
            GinIndex(fields=["applicable_types"], name="idx_criterion_types"),
        ]

    def __str__(self) -> str:
        return f"Criterion({self.code}@{self.rubric_version_id})"
