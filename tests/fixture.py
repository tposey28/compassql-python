"""Shared test fixture: schema matching the TS test/fixture.ts."""
from __future__ import annotations

from compassql.query.expandedtype import ExpandedType
from compassql.schema import FieldSchema, FieldStats, PrimitiveType, Schema


def _stats(name: str, distinct: int) -> FieldStats:
    return FieldStats(field=name, count=distinct, distinct=distinct, unique={})


def _qs(name: str, distinct: int = 100) -> FieldSchema:
    return FieldSchema(name=name, type=PrimitiveType.NUMBER, vl_type=ExpandedType.QUANTITATIVE, stats=_stats(name, distinct))


def _ts(name: str, distinct: int = 100) -> FieldSchema:
    return FieldSchema(name=name, type=PrimitiveType.DATETIME, vl_type=ExpandedType.TEMPORAL, stats=_stats(name, distinct))


def _os(name: str, distinct: int = 6) -> FieldSchema:
    return FieldSchema(name=name, type=PrimitiveType.STRING, vl_type=ExpandedType.ORDINAL, stats=_stats(name, distinct))


def _ns(name: str, distinct: int = 6) -> FieldSchema:
    return FieldSchema(name=name, type=PrimitiveType.STRING, vl_type=ExpandedType.NOMINAL, stats=_stats(name, distinct))


_field_schemas = [
    _qs("Q", 100),
    _qs("Q1", 100),
    _qs("Q2", 100),
    _qs("Q5", 5),
    _qs("Q10", 10),
    _qs("Q15", 15),
    _qs("Q20", 20),
    _ts("T", 100),
    _ts("T1", 100),
    _os("O", 6),
    _os("O_10", 10),
    _os("O_20", 20),
    _os("O_100", 100),
    _ns("N", 6),
    _ns("N20", 20),
]

schema = Schema(_field_schemas)
