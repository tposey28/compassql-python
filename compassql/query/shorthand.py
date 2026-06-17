from __future__ import annotations

import json
from typing import Any, Callable, Optional, Union

from compassql.propindex import PropIndex
from compassql.property import (
    Property,
    DEFAULT_PROP_PRECEDENCE,
    SORT_PROPS,
    VIEW_PROPS,
    is_encoding_nested_parent,
    get_encoding_nested_prop,
    to_key,
)
from compassql.wildcard import is_wildcard, is_short_wildcard, SHORT_WILDCARD
from compassql.query.encoding import (
    EncodingQuery,
    _get,
    is_auto_count_query,
    is_disabled_auto_count_query,
    is_enabled_auto_count_query,
    is_field_query,
    is_value_query,
)

Replacer = Callable[[str], str]

# Channels that support each nested property
PROPERTY_SUPPORTED_CHANNELS: dict[str, dict[str, bool]] = {
    "axis": {"x": True, "y": True, "row": True, "column": True},
    "legend": {"color": True, "opacity": True, "size": True, "shape": True},
    "scale": {"x": True, "y": True, "color": True, "opacity": True, "row": True, "column": True, "size": True, "shape": True},
    "sort": {"x": True, "y": True, "path": True, "order": True},
    "stack": {"x": True, "y": True},
}


def get_replacer(replace: Optional[dict[str, str]]) -> Replacer:
    def replacer(s: str) -> str:
        if replace and replace.get(s) is not None:
            return replace[s]
        return s
    return replacer


def get_replacer_index(replace_index: PropIndex[dict[str, str]]) -> PropIndex[Replacer]:
    return replace_index.map(get_replacer)


REPLACE_NONE: PropIndex[Replacer] = PropIndex()

# Build INCLUDE_ALL — all props set to True
INCLUDE_ALL: PropIndex[bool] = PropIndex()
for _p in list(DEFAULT_PROP_PRECEDENCE) + list(SORT_PROPS) + [Property.TRANSFORM, Property.STACK] + list(VIEW_PROPS):
    INCLUDE_ALL.set(_p, True)


def _value(v: Any, replacer: Optional[Replacer]) -> Any:
    if is_wildcard(v):
        if not is_short_wildcard(v) and isinstance(v, dict) and v.get("enum"):
            return SHORT_WILDCARD + json.dumps(v["enum"])
        elif hasattr(v, "enum") and v.enum is not None and not is_short_wildcard(v):
            return SHORT_WILDCARD + json.dumps(v.enum)
        return SHORT_WILDCARD
    if replacer:
        return replacer(str(v))
    return v


def _replace(v: Any, replacer: Optional[Replacer]) -> Any:
    if replacer:
        return replacer(str(v))
    return v


def spec(
    spec_q: Any,
    include: PropIndex[bool] = INCLUDE_ALL,
    replace: PropIndex[Replacer] = REPLACE_NONE,
) -> str:
    parts: list[str] = []

    if include.get(Property.MARK):
        parts.append(str(_value(spec_q.mark, replace.get(Property.MARK))))

    if spec_q.transform and len(spec_q.transform) > 0:
        parts.append(f"transform:{json.dumps(spec_q.transform)}")

    stack_info = None
    if include.get(Property.STACK):
        from compassql.query.spec import has_required_stack_properties, get_stack_offset, get_stack_channel
        if has_required_stack_properties(spec_q):
            stack_offset = get_stack_offset(spec_q)
            stack_channel = get_stack_channel(spec_q)
            if stack_offset and stack_channel:
                stack_info = {"offset": stack_offset, "fieldChannel": stack_channel}

    if spec_q.encodings:
        enc_parts: list[str] = []
        for enc_q in spec_q.encodings:
            if is_disabled_auto_count_query(enc_q):
                continue
            if stack_info and _get(enc_q, "channel") == stack_info["fieldChannel"]:
                # inject stack offset into encoding shorthand
                patched = dict(enc_q.__dict__) if hasattr(enc_q, "__dict__") else dict(enc_q)
                patched["stack"] = stack_info["offset"]
                from compassql.query.encoding import FieldQuery
                enc_str = encoding(FieldQuery(**{k: v for k, v in patched.items() if k in FieldQuery.__dataclass_fields__}), include, replace)
            else:
                enc_str = encoding(enc_q, include, replace)
            if enc_str:
                enc_parts.append(enc_str)
        enc_parts.sort()
        if enc_parts:
            parts.append("|".join(enc_parts))

    for view_prop in VIEW_PROPS:
        prop_str = str(view_prop)
        if include.get(view_prop):
            val = getattr(spec_q, prop_str, None)
            if val is not None:
                parts.append(f"{prop_str}={json.dumps(val)}")

    return "|".join(parts)


def encoding(
    enc_q: EncodingQuery,
    include: PropIndex[bool] = INCLUDE_ALL,
    replace: PropIndex[Replacer] = REPLACE_NONE,
) -> str:
    parts: list[str] = []

    if include.get(Property.CHANNEL):
        parts.append(str(_value(_get(enc_q, "channel"), replace.get(Property.CHANNEL))))

    if is_field_query(enc_q):
        fd_str = field_def(enc_q, include, replace)
        if fd_str:
            parts.append(fd_str)
    elif is_value_query(enc_q):
        parts.append(str(_get(enc_q, "value")))
    elif is_auto_count_query(enc_q):
        parts.append("autocount()")

    return ":".join(parts)


def field_def(
    enc_q: EncodingQuery,
    include: PropIndex[bool] = INCLUDE_ALL,
    replacer: PropIndex[Replacer] = REPLACE_NONE,
) -> Optional[str]:
    if include.get(Property.AGGREGATE) and is_disabled_auto_count_query(enc_q):
        return "-"

    fn_str = _func(enc_q, include, replacer)
    props = _field_def_props(enc_q, include, replacer)

    field_and_params: Optional[str] = None

    if is_field_query(enc_q):
        field_val = _get(enc_q, "field")
        field_and_params = str(_value(field_val, replacer.get("field"))) if include.get("field") else "..."

        if include.get(Property.TYPE):
            type_val = _get(enc_q, "type")
            if is_wildcard(type_val):
                field_and_params += f",{_value(type_val, replacer.get(Property.TYPE))}"
            else:
                type_short = str(type_val or "quantitative")[0]
                field_and_params += f",{_value(type_short, replacer.get(Property.TYPE))}"

        for p in props:
            val = p["value"]
            val_str = f"[{val}]" if isinstance(val, list) else str(val)
            field_and_params += f",{p['key']}={val_str}"

    elif is_auto_count_query(enc_q):
        field_and_params = "*,q"

    if not field_and_params:
        return None

    if fn_str is not None:
        if isinstance(fn_str, str):
            fn_prefix = fn_str
        else:
            fn_prefix = SHORT_WILDCARD + (json.dumps(fn_str) if fn_str else "")
        return f"{fn_prefix}({field_and_params})"

    return field_and_params


def _func(field_q: Any, include: PropIndex[bool], replacer: PropIndex[Replacer]) -> Any:
    aggregate = _get(field_q, "aggregate")
    time_unit = _get(field_q, "timeUnit")
    bin_ = _get(field_q, "bin")

    if include.get(Property.AGGREGATE) and aggregate and not is_wildcard(aggregate):
        return _replace(aggregate, replacer.get(Property.AGGREGATE))
    elif include.get(Property.AGGREGATE) and is_enabled_auto_count_query(field_q):
        return _replace("count", replacer.get(Property.AGGREGATE))
    elif include.get(Property.TIMEUNIT) and time_unit and not is_wildcard(time_unit):
        return _replace(time_unit, replacer.get(Property.TIMEUNIT))
    elif include.get(Property.BIN) and bin_ and not is_wildcard(bin_):
        return "bin"
    else:
        fn: Any = None
        for prop in [Property.AGGREGATE, Property.AUTOCOUNT, Property.TIMEUNIT, Property.BIN]:
            val = _get(field_q, prop)
            if include.get(prop) and val and is_wildcard(val):
                fn = fn or {}
                fn[prop] = val if is_short_wildcard(val) else (val.enum if hasattr(val, "enum") else val.get("enum"))
        has_fn = _get(field_q, "hasFn")
        if fn and has_fn:
            fn["hasFn"] = True
        return fn


def _field_def_props(field_q: Any, include: PropIndex[bool], replacer: PropIndex[Replacer]) -> list[dict[str, Any]]:
    props: list[dict[str, Any]] = []
    bin_ = _get(field_q, "bin")

    if not isinstance(bin_, bool) and not is_short_wildcard(bin_) and isinstance(bin_, dict):
        for child, child_val in bin_.items():
            nested_prop = get_encoding_nested_prop("bin", child)
            if nested_prop and include.get(nested_prop) and child_val is not None:
                props.append({"key": child, "value": _value(child_val, replacer.get(nested_prop))})
        props.sort(key=lambda p: p["key"])

    channel = _get(field_q, "channel")
    for parent in [Property.SCALE, Property.SORT, Property.STACK, Property.AXIS, Property.LEGEND]:
        supported = PROPERTY_SUPPORTED_CHANNELS.get(parent, {})
        if not is_wildcard(channel) and supported and not supported.get(str(channel)):
            continue
        parent_val = _get(field_q, parent)
        if not include.get(parent) or parent_val is None:
            continue

        if isinstance(parent_val, bool) or parent_val is None:
            props.append({"key": str(parent), "value": parent_val or False})
        elif isinstance(parent_val, str):
            props.append({"key": str(parent), "value": _replace(json.dumps(parent_val), replacer.get(parent))})
        elif isinstance(parent_val, dict):
            nested_children: list[dict[str, Any]] = []
            for child, child_val in parent_val.items():
                nested_prop = get_encoding_nested_prop(parent, child)
                if nested_prop and include.get(nested_prop) and child_val is not None:
                    nested_children.append({"key": child, "value": _value(child_val, replacer.get(nested_prop))})
            if nested_children:
                nested_children.sort(key=lambda p: p["key"])
                nested_obj = {p["key"]: p["value"] for p in nested_children}
                props.append({"key": str(parent), "value": json.dumps(nested_obj)})

    return props


# ---------------------------------------------------------------------------
# parse: shorthand string → SpecQuery
# ---------------------------------------------------------------------------

def parse(shorthand: str) -> Any:
    from compassql.query.spec import SpecQuery
    from compassql.query.encoding import FieldQuery

    parts = shorthand.split("|")
    spec_q = SpecQuery(mark=parts[0], encodings=[])

    _CHANNELS = {
        "x", "y", "x2", "y2", "xOffset", "yOffset", "color", "opacity",
        "fillOpacity", "strokeOpacity", "strokeWidth", "size", "shape",
        "row", "column", "facet", "text", "tooltip", "href", "key",
        "latitude", "longitude", "latitude2", "longitude2", "order",
        "detail", "description",
    }

    for i in range(1, len(parts)):
        part = parts[i]
        split_part = _split_with_tail(part, ":", 1)
        split_key = split_part[0]
        split_val = split_part[1] if len(split_part) > 1 else ""

        if split_key in _CHANNELS or split_key == SHORT_WILDCARD:
            enc_q = _shorthand_parser_encoding(split_key, split_val)
            spec_q.encodings.append(enc_q)
            continue

        if split_key == "transform":
            spec_q.transform = json.loads(split_val)
            continue

    return spec_q


def _split_with_tail(s: str, delim: str, count: int) -> list[str]:
    result: list[str] = []
    last = 0
    for _ in range(count):
        idx = s.find(delim, last)
        if idx != -1:
            result.append(s[last:idx])
            last = idx + 1
        else:
            break
    result.append(s[last:])
    while len(result) < count + 1:
        result.append("")
    return result


def _shorthand_parser_encoding(channel: str, field_def_shorthand: str) -> Any:
    from compassql.query.encoding import FieldQuery, AutoCountQuery, ValueQuery
    if "(" in field_def_shorthand:
        mixins = _parse_fn(field_def_shorthand)
    else:
        mixins = _parse_raw_field_def(_split_with_tail(field_def_shorthand, ",", 2))

    mixins["channel"] = channel

    if "autoCount" in mixins:
        return AutoCountQuery(**{k: v for k, v in mixins.items() if k in AutoCountQuery.__dataclass_fields__})
    if "value" in mixins:
        return ValueQuery(**{k: v for k, v in mixins.items() if k in ValueQuery.__dataclass_fields__})
    return FieldQuery(**{k: v for k, v in mixins.items() if k in FieldQuery.__dataclass_fields__})


_TYPE_FULL_NAMES: dict[str, str] = {
    "Q": "quantitative", "O": "ordinal", "N": "nominal", "T": "temporal",
    "QUANTITATIVE": "quantitative", "ORDINAL": "ordinal",
    "NOMINAL": "nominal", "TEMPORAL": "temporal",
}

_AGGREGATE_OPS = {
    "argmax", "argmin", "average", "count", "distinct", "max", "mean",
    "median", "min", "missing", "product", "q1", "q3", "ci0", "ci1",
    "stderr", "stdev", "stdevp", "sum", "valid", "values", "variance", "variancep",
}

_TIME_UNITS = {
    "year", "quarter", "month", "week", "day", "dayofyear", "date",
    "hours", "minutes", "seconds", "milliseconds",
    "yearquarter", "yearquartermonth", "yearmonth", "yearmonthdate",
    "yearmonthdatehours", "yearmonthdatehoursminutes",
    "yearmonthdatehoursminutesseconds", "quartermonth", "monthdate",
    "monthdatehours", "hoursminutes", "hoursminutesseconds",
    "minutesseconds", "secondsmilliseconds",
}


def _parse_raw_field_def(parts: list[str]) -> dict[str, Any]:
    field_q: dict[str, Any] = {}
    field_q["field"] = parts[0] if parts else None
    raw_type = parts[1].upper() if len(parts) > 1 else "?"
    field_q["type"] = _TYPE_FULL_NAMES.get(raw_type, SHORT_WILDCARD)

    part_params = parts[2] if len(parts) > 2 else ""
    i = 0
    while i < len(part_params):
        eq_idx = part_params.find("=", i)
        if eq_idx == -1:
            break
        prop = part_params[i:eq_idx]
        rest_start = eq_idx + 1
        if rest_start < len(part_params) and part_params[rest_start] == "{":
            close = _get_closing_index(rest_start, part_params, "}")
            val = json.loads(part_params[rest_start:close + 1])
            i = close + 2
        elif rest_start < len(part_params) and part_params[rest_start] == "[":
            close = _get_closing_index(rest_start, part_params, "]")
            val = json.loads(part_params[rest_start:close + 1])
            i = close + 2
        else:
            next_comma = part_params.find(",", rest_start)
            if next_comma == -1:
                next_comma = len(part_params)
            val = json.loads(part_params[rest_start:next_comma])
            i = next_comma + 1

        if is_encoding_nested_parent(prop):
            field_q[prop] = val
        else:
            field_q.setdefault("bin", {})
            if isinstance(field_q["bin"], dict):
                field_q["bin"][prop] = val

    return field_q


def _get_closing_index(opening: int, s: str, closing_char: str) -> int:
    for i in range(opening, len(s)):
        if s[i] == closing_char:
            return i
    return len(s) - 1


def _parse_fn(field_def_shorthand: str) -> dict[str, Any]:
    field_q: dict[str, Any] = {}

    if field_def_shorthand[0] == "?":
        close = _get_closing_index(1, field_def_shorthand, "}")
        fn_enum_index = json.loads(field_def_shorthand[1:close + 1])
        for enc_prop, val in fn_enum_index.items():
            if isinstance(val, list):
                field_q[enc_prop] = {"enum": val}
            else:
                field_q[enc_prop] = val
        inner = field_def_shorthand[close + 2: len(field_def_shorthand) - 1]
        field_q.update(_parse_raw_field_def(_split_with_tail(inner, ",", 2)))
        return field_q

    fn_end = field_def_shorthand.index("(")
    func_name = field_def_shorthand[:fn_end]
    inside = field_def_shorthand[fn_end + 1: len(field_def_shorthand) - 1]
    inside_parts = _split_with_tail(inside, ",", 2)

    if func_name in _AGGREGATE_OPS:
        return {"aggregate": func_name, **_parse_raw_field_def(inside_parts)}
    elif func_name in _TIME_UNITS:
        return {"timeUnit": func_name, **_parse_raw_field_def(inside_parts)}
    elif func_name == "bin":
        return {"bin": {}, **_parse_raw_field_def(inside_parts)}
    return field_q


def vlspec(
    vl_spec: dict[str, Any],
    include: PropIndex[bool] = INCLUDE_ALL,
    replace_fn: PropIndex[Replacer] = REPLACE_NONE,
) -> str:
    from compassql.query.spec import from_spec
    spec_q = from_spec(vl_spec)
    return spec(spec_q, include, replace_fn)
