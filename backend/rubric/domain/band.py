"""Band / Severity / OverrideCode literal mirrors of platform_core enums.

Domain layer must not depend on Django, so this module re-declares the
canonical value sets as plain str-enums. The values match
``platform_core.domain.enums`` byte-for-byte; the link is verified by
``tests/test_rubric_enum_alignment.py``.
"""

from __future__ import annotations

from enum import StrEnum


class Band(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    NOT_ANALYZABLE = "not_analyzable"


class Severity(StrEnum):
    CRITICAL = "critical"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    UNVERIFIABLE = "unverifiable"


class OverrideCode(StrEnum):
    """The 11 critical overrides defined by RUBRICA_CONTRATO §2.2 / DOMAIN §6.6."""

    ART_1605_CC = "art_1605_cc"
    ART_1613_CC = "art_1613_cc"
    ART_1644_CC = "art_1644_cc"
    ART_1425_CC = "art_1425_cc"
    ART_3_IVU_FAMILY_HOMESTEAD = "art_3_ivu_family_homestead"
    ART_5_LPC_NON_WAIVABLE = "art_5_lpc_non_waivable"
    ART_12_LPC = "art_12_lpc"
    ART_13_LPC = "art_13_lpc"
    ART_18_LPC_BLANK_SIGNATURE = "art_18_lpc_blank_signature"
    ART_17H_LPC_ARBITRATION = "art_17h_lpc_arbitration"
    ART_58_FSV = "art_58_fsv"


__all__ = ["Band", "OverrideCode", "Severity"]
