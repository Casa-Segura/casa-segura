"""BenchmarkCatalog lookup cache (CS-135).

Wraps a `BenchmarkVersion` queryset into an in-memory lookup map keyed by
`benchmark_key`, so the assembler can pull benchmark values without N+1 DB
hits. Constructed once per analysis run.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from economics.infrastructure.django.models import BenchmarkVersion, EconomicBenchmark


@dataclass(frozen=True)
class CatalogEntry:
    """Lightweight subset of EconomicBenchmark needed for assembly."""

    benchmark_key: str
    value_min: Decimal | None
    value_max: Decimal | None
    value_default: Decimal | None
    unit: str
    source: str

    @property
    def value(self) -> Decimal | None:
        return self.value_default if self.value_default is not None else self.value_min


class BenchmarkCatalog:
    """In-memory map for one `BenchmarkVersion` row."""

    def __init__(self, version: BenchmarkVersion, entries: dict[str, CatalogEntry]) -> None:
        self._version = version
        self._entries = entries

    @property
    def version(self) -> str:
        return self._version.version

    def get(self, benchmark_key: str) -> CatalogEntry | None:
        return self._entries.get(benchmark_key)

    @classmethod
    def from_db(cls, version: BenchmarkVersion) -> BenchmarkCatalog:
        """Hydrate a catalog from the DB rows attached to `version`."""

        rows = EconomicBenchmark.objects.filter(benchmark_version=version)
        entries: dict[str, CatalogEntry] = {}
        for row in rows:
            entries[row.benchmark_key] = CatalogEntry(
                benchmark_key=row.benchmark_key,
                value_min=row.value_min,
                value_max=row.value_max,
                value_default=row.value_default,
                unit=row.unit,
                source=row.source,
            )
        return cls(version, entries)


__all__ = ["BenchmarkCatalog", "CatalogEntry"]
