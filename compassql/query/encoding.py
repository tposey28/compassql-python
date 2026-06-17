from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from compassql.wildcard import is_wildcard, SHORT_WILDCARD, Wildcard
from compassql.query.expandedtype import ExpandedType


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

BinQuery = dict[str, Any]       # FlatQueryWithEnableFlag<BinParams>
ScaleQuery = dict[str, Any]     # FlatQueryWithEnableFlag<Scale>
AxisQuery = dict[str, Any]      # FlatQueryWithEnableFlag<Axis>
LegendQuery = dict[str, Any]    # FlatQueryWithEnableFlag<Legend>

SortValue = Union[str, dict[str, Any]]  # SortOrder | EncodingSortField


@dataclass
class EncodingQueryBase:
    channel: Any  # WildcardProperty[Channel]
    description: Optional[str] = None


@dataclass
class FieldQuery(EncodingQueryBase):
    field: Any = None                  # WildcardProperty[str]
    type: Any = None                   # WildcardProperty[ExpandedType]
    aggregate: Any = None              # WildcardProperty[AggregateOp]
    timeUnit: Any = None               # WildcardProperty[TimeUnit]
    bin: Any = None                    # bool | BinQuery | SHORT_WILDCARD
    scale: Any = None                  # bool | ScaleQuery | SHORT_WILDCARD
    sort: Any = None                   # SortValue
    stack: Any = None                  # StackOffset | SHORT_WILDCARD
    axis: Any = None                   # bool | AxisQuery | SHORT_WILDCARD
    legend: Any = None                 # bool | LegendQuery | SHORT_WILDCARD
    format: Optional[str] = None
    hasFn: Optional[bool] = None


@dataclass
class ValueQuery(EncodingQueryBase):
    value: Any = None                  # WildcardProperty[bool|int|str]


@dataclass
class AutoCountQuery(EncodingQueryBase):
    autoCount: Any = None              # WildcardProperty[bool]
    type: str = "quantitative"


EncodingQuery = Union[FieldQuery, ValueQuery, AutoCountQuery]

_FIELD_QUERY_KEYS = frozenset({
    "channel", "description", "field", "type", "aggregate",
    "timeUnit", "bin", "scale", "sort", "stack", "axis",
    "legend", "format", "hasFn",
})


def encoding_query_from_dict(d: dict) -> "EncodingQuery":
    """Convert a plain encoding dict to the appropriate dataclass."""
    if "value" in d:
        return ValueQuery(
            channel=d.get("channel"),
            description=d.get("description"),
            value=d.get("value"),
        )
    if "autoCount" in d:
        return AutoCountQuery(
            channel=d.get("channel"),
            description=d.get("description"),
            autoCount=d.get("autoCount"),
            type=d.get("type", "quantitative"),
        )
    return FieldQuery(**{k: v for k, v in d.items() if k in _FIELD_QUERY_KEYS})


# ---------------------------------------------------------------------------
# Type guards
# ---------------------------------------------------------------------------

def is_value_query(enc_q: Any) -> bool:
    return isinstance(enc_q, ValueQuery)


def is_field_query(enc_q: Any) -> bool:
    return isinstance(enc_q, FieldQuery)


def is_auto_count_query(enc_q: Any) -> bool:
    return isinstance(enc_q, AutoCountQuery)


def is_disabled_auto_count_query(enc_q: Any) -> bool:
    return isinstance(enc_q, AutoCountQuery) and enc_q.autoCount is False


def is_enabled_auto_count_query(enc_q: Any) -> bool:
    return isinstance(enc_q, AutoCountQuery) and enc_q.autoCount is True


def _get(obj: Any, attr: str) -> Any:
    return getattr(obj, attr, None)


# ---------------------------------------------------------------------------
# Helpers for is_dimension / is_measure / is_continuous
# ---------------------------------------------------------------------------

def is_dimension(enc_q: EncodingQuery) -> bool:
    if not is_field_query(enc_q):
        return False
    type_ = _get(enc_q, "type")
    bin_ = _get(enc_q, "bin")
    time_unit = _get(enc_q, "timeUnit")
    if type_ in (ExpandedType.ORDINAL, ExpandedType.NOMINAL, ExpandedType.KEY, "ordinal", "nominal", "key"):
        return True
    if bin_ and bin_ is not False and not is_wildcard(bin_):
        return True
    if time_unit and not is_wildcard(time_unit):
        return True
    return False


def is_measure(enc_q: EncodingQuery) -> bool:
    if is_field_query(enc_q):
        type_ = _get(enc_q, "type")
        return not is_dimension(enc_q) and type_ != "temporal"
    return is_auto_count_query(enc_q)


def is_continuous(enc_q: EncodingQuery) -> bool:
    if is_field_query(enc_q):
        type_ = _get(enc_q, "type")
        bin_ = _get(enc_q, "bin")
        time_unit = _get(enc_q, "timeUnit")
        if type_ in ("quantitative",) and not bin_:
            return True
        if type_ == "temporal" and not time_unit:
            return True
        return False
    return is_auto_count_query(enc_q)


# ---------------------------------------------------------------------------
# to_encoding: convert list of EncodingQuery → dict (Vega-Lite encoding object)
# ---------------------------------------------------------------------------

_DEFAULT_PROPS = [
    "aggregate", "bin", "timeUnit", "field", "type",
    "scale", "sort", "axis", "legend", "stack", "format",
]


def to_encoding(enc_qs: list[EncodingQuery], params: dict[str, Any]) -> Optional[dict[str, Any]]:
    wildcard_mode = params.get("wildcardMode", "skip")
    encoding: dict[str, Any] = {}

    for enc_q in enc_qs:
        if is_disabled_auto_count_query(enc_q):
            continue

        channel = _get(enc_q, "channel")
        if is_wildcard(channel):
            raise ValueError("Cannot convert wildcard channel to a fixed channel")

        if is_value_query(enc_q):
            channel_def = _to_value_def(enc_q)
        else:
            channel_def = _to_field_def(enc_q, params)

        if channel_def is None:
            if wildcard_mode == "null":
                return None
            continue

        encoding[channel] = channel_def

    return encoding


def _to_value_def(value_q: Any) -> Optional[dict[str, Any]]:
    value = _get(value_q, "value")
    if is_wildcard(value):
        return None
    return {"value": value}


def _to_field_def(enc_q: Any, params: dict[str, Any] = {}) -> Optional[dict[str, Any]]:
    props = params.get("props", _DEFAULT_PROPS)
    wildcard_mode = params.get("wildcardMode", "skip")

    if is_field_query(enc_q):
        field_def: dict[str, Any] = {}
        for prop in props:
            enc_prop = _get(enc_q, prop)
            if is_wildcard(enc_prop):
                if wildcard_mode == "skip":
                    continue
                return None
            if enc_prop is not None:
                if prop == "bin" and enc_prop is False:
                    continue
                elif prop == "type" and enc_prop == "key":
                    field_def["type"] = "nominal"
                else:
                    field_def[prop] = enc_prop
        return field_def
    else:
        auto_count = _get(enc_q, "autoCount")
        if auto_count is False:
            raise ValueError("Cannot convert {autoCount: false} into a field def")
        return {"aggregate": "count", "field": "*", "type": "quantitative"}
