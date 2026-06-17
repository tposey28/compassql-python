from __future__ import annotations

from enum import Enum

from compassql.vegalite_types import VLType


class ExpandedType(str, Enum):
    QUANTITATIVE = "quantitative"
    ORDINAL = "ordinal"
    TEMPORAL = "temporal"
    NOMINAL = "nominal"
    KEY = "key"


def is_discrete(field_type: str) -> bool:
    return field_type in (ExpandedType.ORDINAL, ExpandedType.NOMINAL, ExpandedType.KEY)
