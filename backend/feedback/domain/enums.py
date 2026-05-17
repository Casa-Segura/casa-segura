"""Feedback enums — CS-336."""

from __future__ import annotations

from enum import StrEnum


class FeedbackCategory(StrEnum):
    """Categories the user picks when reporting a discrepancy."""

    CLASSIFICATION = "classification"
    CITATION = "citation"
    ECONOMIC_FIGURE = "economic_figure"
    UI = "ui"
    OTHER = "other"


__all__ = ["FeedbackCategory"]
