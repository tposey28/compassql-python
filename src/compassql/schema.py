from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

import pandas as pd

from compassql.config import DEFAULT_QUERY_CONFIG, QueryConfig


class PrimitiveType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATETIME = "datetime"


# Vega-Lite measure types + KEY extension
class ExpandedType(str, Enum):
    QUANTITATIVE = "quantitative"
    ORDINAL = "ordinal"
    TEMPORAL = "temporal"
    NOMINAL = "nominal"
    KEY = "key"


def is_discrete(field_type: Any) -> bool:
    return field_type in (ExpandedType.ORDINAL, ExpandedType.NOMINAL, ExpandedType.KEY)


# Sort order for field display (mirrors TS)
_VL_TYPE_ORDER = {
    ExpandedType.NOMINAL: 0,
    ExpandedType.KEY: 1,
    ExpandedType.ORDINAL: 2,
    ExpandedType.TEMPORAL: 3,
    ExpandedType.QUANTITATIVE: 4,
}

# Augmented time-unit cardinalities (from vega-time)
_TIMEUNIT_CARDINALITY: dict[str, int] = {
    "seconds": 60,
    "minutes": 60,
    "hours": 24,
    "day": 7,
    "date": 31,
    "month": 12,
    "quarter": 4,
    "milliseconds": 1000,
}


@dataclass
class FieldStats:
    """Lightweight stats profile for a field."""
    field: str
    count: int
    distinct: int
    unique: dict  # value → frequency
    min: Any = None
    max: Any = None


@dataclass
class FieldSchema:
    name: str
    type: PrimitiveType
    vl_type: ExpandedType
    stats: FieldStats
    original_index: int = 0
    index: int = 0
    title: Optional[str] = None
    description: Optional[str] = None
    ordinal_domain: Optional[list] = None
    bin_stats: dict[str, FieldStats] = field(default_factory=dict)
    time_stats: dict[str, FieldStats] = field(default_factory=dict)


def _infer_primitive_type(series: pd.Series) -> PrimitiveType:
    dtype = series.dtype
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return PrimitiveType.DATETIME
    if pd.api.types.is_float_dtype(dtype):
        return PrimitiveType.NUMBER
    if pd.api.types.is_integer_dtype(dtype):
        return PrimitiveType.INTEGER
    return PrimitiveType.STRING


def _field_stats(series: pd.Series, name: str) -> FieldStats:
    count = int(series.count())
    value_counts = series.value_counts(dropna=False)
    unique: dict = {str(k): int(v) for k, v in value_counts.items()}
    distinct = int(series.nunique(dropna=False))
    try:
        min_val = series.min()
        max_val = series.max()
    except Exception:
        min_val = max_val = None
    return FieldStats(field=name, count=count, distinct=distinct, unique=unique, min=min_val, max=max_val)


def _bin_stats(max_bins: int, stats: FieldStats) -> FieldStats:
    """Compute binned stats for a quantitative field."""
    try:
        min_val = float(stats.min)
        max_val = float(stats.max)
    except (TypeError, ValueError):
        return copy.copy(stats)

    if min_val == max_val:
        result = copy.copy(stats)
        result.distinct = 1
        return result

    # Simple linear binning (mirrors datalib's bin algorithm)
    import math
    raw_step = (max_val - min_val) / max_bins

    # An all-NaN or empty column gives min == max == NaN, so raw_step is NaN;
    # an unbounded one gives inf. Upstream JS degrades here rather than throwing
    # (Math.log10(NaN) is NaN, Math.floor(NaN) is NaN, Math.pow(10, NaN) is NaN),
    # but math.floor(nan) raises ValueError and math.floor(inf) raises
    # OverflowError. Return the field unbinned so the port matches upstream's
    # "no usable bins" outcome instead of failing the whole schema build.
    # (raw_step <= 0 is unreachable while min == max returns above, but log10(0)
    # is -inf and would raise the same way, so it is folded into the guard.)
    if not math.isfinite(raw_step) or raw_step <= 0:
        return copy.copy(stats)

    magnitude = 10 ** math.floor(math.log10(raw_step))
    nice_steps = [1, 2, 5, 10]
    step = magnitude * next((s for s in nice_steps if s * magnitude >= raw_step), 10)
    start = math.floor(min_val / step) * step
    stop = math.ceil(max_val / step) * step

    new_unique: dict = {}
    for val_str, freq in stats.unique.items():
        try:
            val = float(val_str)
            bucket = math.floor((val - start) / step) * step + start
            bucket_key = str(bucket)
        except (TypeError, ValueError):
            bucket_key = str(None)
        new_unique[bucket_key] = new_unique.get(bucket_key, 0) + freq

    result = copy.copy(stats)
    result.unique = new_unique
    result.distinct = max(1, round((stop - start) / step))
    result.min = start
    result.max = stop
    return result


def _time_stats(time_unit: str, stats: FieldStats) -> FieldStats:
    """Compute time-unit grouped stats for a temporal field."""
    unique: dict = {}
    for date_str, freq in stats.unique.items():
        if date_str in (str(None), "None", "NaT", "nan"):
            key = str(None)
        else:
            try:
                dt = pd.to_datetime(date_str)
                key = str(_truncate_datetime(dt, time_unit))
            except Exception:
                key = "Invalid Date"
        unique[key] = unique.get(key, 0) + freq

    result = copy.copy(stats)
    result.unique = unique
    result.distinct = len(unique)
    return result


def _truncate_datetime(dt: Any, time_unit: str) -> Any:
    """Truncate a datetime to the given time unit."""
    try:
        ts = pd.Timestamp(dt)
        if time_unit == "year":
            return ts.year
        elif time_unit == "month":
            return ts.month
        elif time_unit == "date":
            return ts.day
        elif time_unit == "day":
            return ts.dayofweek
        elif time_unit == "hours":
            return ts.hour
        elif time_unit == "minutes":
            return ts.minute
        elif time_unit == "seconds":
            return ts.second
        elif time_unit == "milliseconds":
            return ts.microsecond // 1000
        elif time_unit == "quarter":
            return ts.quarter
        else:
            return str(ts)
    except Exception:
        return "Invalid Date"


class Schema:
    def __init__(self, field_schemas: list[FieldSchema]) -> None:
        # Sort: by vl_type order first, then by name
        field_schemas = sorted(
            field_schemas,
            key=lambda fs: (_VL_TYPE_ORDER.get(fs.vl_type, 99), fs.name),
        )
        for i, fs in enumerate(field_schemas):
            fs.index = i
        self._field_schemas: list[FieldSchema] = field_schemas
        self._field_schema_index: dict[str, FieldSchema] = {fs.name: fs for fs in field_schemas}

    @classmethod
    def build_from_data(
        cls,
        data: Union[list[dict], "pd.DataFrame"],
        opt: Optional[QueryConfig] = None,
    ) -> "Schema":
        if opt is None:
            opt = DEFAULT_QUERY_CONFIG
        if not isinstance(data, pd.DataFrame):
            df = pd.DataFrame(data)
        else:
            df = data

        # Attempt datetime parsing for object columns
        for col in df.columns:
            if df[col].dtype == object:
                try:
                    parsed = pd.to_datetime(df[col])
                    df = df.copy()
                    df[col] = parsed
                except Exception:
                    pass

        field_schemas: list[FieldSchema] = []
        for i, col in enumerate(df.columns):
            series = df[col]
            ptype = _infer_primitive_type(series)
            stats = _field_stats(series, col)
            count = stats.count
            distinct = stats.distinct

            if ptype == PrimitiveType.NUMBER:
                vl_type = ExpandedType.QUANTITATIVE
            elif ptype == PrimitiveType.INTEGER:
                proportion = distinct / count if count > 0 else 1.0
                if distinct < opt.number_nominal_limit and proportion < opt.number_nominal_proportion:
                    vl_type = ExpandedType.NOMINAL
                else:
                    vl_type = ExpandedType.QUANTITATIVE
            elif ptype == PrimitiveType.DATETIME:
                vl_type = ExpandedType.TEMPORAL
            else:
                vl_type = ExpandedType.NOMINAL

            # Promote high-cardinality nominal to KEY
            if vl_type == ExpandedType.NOMINAL and count > 0:
                pct_unique = distinct / count
                if pct_unique > opt.min_percent_unique_for_key and count > opt.min_cardinality_for_key:
                    vl_type = ExpandedType.KEY

            fs = FieldSchema(
                name=col,
                type=ptype,
                vl_type=vl_type,
                stats=stats,
                original_index=i,
            )

            enum_cfg = opt.enum or {}
            bin_props = enum_cfg.get("binProps", {})
            maxbins_list = bin_props.get("maxbins", [5, 10, 20])
            time_units = enum_cfg.get("timeUnit", [None, "year", "month", "minutes", "seconds"])

            if vl_type == ExpandedType.QUANTITATIVE:
                for mb in maxbins_list:
                    if mb is not None:
                        fs.bin_stats[str(mb)] = _bin_stats(mb, stats)
            elif vl_type == ExpandedType.TEMPORAL:
                for tu in time_units:
                    if tu is not None:
                        fs.time_stats[tu] = _time_stats(tu, stats)

            field_schemas.append(fs)

        return cls(field_schemas)

    def field_names(self) -> list[str]:
        return [fs.name for fs in self._field_schemas]

    @property
    def field_schemas(self) -> list[FieldSchema]:
        return self._field_schemas

    def field_schema(self, field_name: str) -> Optional[FieldSchema]:
        return self._field_schema_index.get(field_name)

    def table_schema(self) -> list[FieldSchema]:
        return sorted(self._field_schemas, key=lambda fs: fs.original_index)

    def primitive_type(self, field_name: str) -> Optional[PrimitiveType]:
        fs = self._field_schema_index.get(field_name)
        return fs.type if fs else None

    def vl_type(self, field_name: str) -> Optional[ExpandedType]:
        fs = self._field_schema_index.get(field_name)
        return fs.vl_type if fs else None

    def has_field(self, field_name: str) -> bool:
        return field_name in self._field_schema_index

    def fields(self) -> list[str]:
        return self.field_names()

    def cardinality(self, enc_q: dict, augment_time_unit_domain: bool = True, exclude_invalid: bool = False) -> Optional[int]:
        """Compute cardinality of the encoding query's field."""
        field_name = enc_q.get("field")
        fs = self._field_schema_index.get(str(field_name)) if field_name else None

        if enc_q.get("aggregate") or enc_q.get("autoCount"):
            return 1

        if enc_q.get("bin"):
            bin_val = enc_q["bin"]
            if isinstance(bin_val, bool):
                max_bins = 10  # default
            elif isinstance(bin_val, dict):
                max_bins = bin_val.get("maxbins", 10)
            else:
                max_bins = 10
            key = str(max_bins)
            if fs:
                if key not in fs.bin_stats:
                    fs.bin_stats[key] = _bin_stats(max_bins, fs.stats)
                return fs.bin_stats[key].distinct
            return None

        time_unit = enc_q.get("timeUnit")
        if time_unit:
            if augment_time_unit_domain and time_unit in _TIMEUNIT_CARDINALITY:
                return _TIMEUNIT_CARDINALITY[time_unit]
            if fs:
                if time_unit not in fs.time_stats:
                    fs.time_stats[time_unit] = _time_stats(time_unit, fs.stats)
                tu_stats = fs.time_stats[time_unit]
                if exclude_invalid:
                    invalid = sum(1 for k in tu_stats.unique if k in (str(None), "Invalid Date"))
                    return tu_stats.distinct - invalid
                return tu_stats.distinct
            return None

        if fs:
            if exclude_invalid:
                invalid = sum(1 for k in fs.stats.unique if k in ("nan", str(None), "NaN"))
                return fs.stats.distinct - invalid
            return fs.stats.distinct
        return None

    def domain(self, field_query: dict) -> list:
        """Return the domain of values for a field."""
        field_name = field_query.get("field", "")
        fs = self._field_schema_index.get(str(field_name))
        if not fs:
            return []

        if fs.vl_type == ExpandedType.QUANTITATIVE:
            return [float(fs.stats.min), float(fs.stats.max)]
        if fs.type == PrimitiveType.DATETIME:
            return [fs.stats.min, fs.stats.max]
        if fs.type in (PrimitiveType.INTEGER, PrimitiveType.NUMBER):
            vals = [float(k) for k in fs.stats.unique if k not in ("nan", str(None))]
            return sorted(vals)
        if fs.vl_type == ExpandedType.ORDINAL and fs.ordinal_domain:
            return fs.ordinal_domain

        domain = [None if k in (str(None), "None") else k for k in fs.stats.unique]
        return sorted(domain, key=lambda x: (x is None, x))

    def stats(self, field_q: dict) -> Optional[FieldStats]:
        field_name = field_q.get("field", "")
        fs = self._field_schema_index.get(str(field_name))
        return fs.stats if fs else None

    def time_unit_has_variation(self, field_q: dict) -> Optional[bool]:
        time_unit = field_q.get("timeUnit")
        if not time_unit:
            return None

        if time_unit == "day":
            date_q = {**field_q, "timeUnit": "date"}
            card = self.cardinality(date_q, augment_time_unit_domain=False, exclude_invalid=True)
            if card is not None and card <= 1:
                return False

        # Check each component part
        _TIMEUNIT_PARTS = ["year", "quarter", "month", "week", "day", "dayofyear",
                           "date", "hours", "minutes", "seconds", "milliseconds"]
        for part in _TIMEUNIT_PARTS:
            if part in time_unit:
                part_q = {**field_q, "timeUnit": part}
                card = self.cardinality(part_q, augment_time_unit_domain=False, exclude_invalid=True)
                if card is not None and card <= 1:
                    return False
        return True
