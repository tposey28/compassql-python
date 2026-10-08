from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar, Union

T = TypeVar("T")

SHORT_WILDCARD: str = "?"


@dataclass
class Wildcard(Generic[T]):
    name: Optional[str] = None
    enum: Optional[list] = None


WildcardProperty = Union[T, "Wildcard[T]", str]


def is_wildcard(prop: Any) -> bool:
    return is_short_wildcard(prop) or is_wildcard_def(prop)


def is_short_wildcard(prop: Any) -> bool:
    return prop == SHORT_WILDCARD


def is_wildcard_def(prop: Any) -> bool:
    if prop is None:
        return False
    if isinstance(prop, list):
        return False
    if isinstance(prop, dict):
        return bool(prop.get("enum")) or bool(prop.get("name"))
    if isinstance(prop, Wildcard):
        return bool(prop.enum) or bool(prop.name)
    return False


def init_wildcard(prop: Any, default_name: str, default_enum: list) -> Wildcard:
    if is_short_wildcard(prop):
        return Wildcard(name=default_name, enum=list(default_enum))
    if isinstance(prop, dict):
        return Wildcard(
            name=prop.get("name") or default_name,
            enum=prop["enum"] if prop.get("enum") is not None else list(default_enum),
        )
    if isinstance(prop, Wildcard):
        return Wildcard(
            name=prop.name or default_name,
            enum=prop.enum if prop.enum is not None else list(default_enum),
        )
    raise ValueError(f"Not a wildcard: {prop}")


def _init_nested_prop_name(full_names: list[str]) -> dict[str, str]:
    """Derive short names from camelCase full names (e.g. 'bandPaddingInner' → 'bpi')."""
    index: dict[str, str] = {}
    has: dict[str, bool] = {}
    for full_name in full_names:
        initial_indices = [0]
        for i, ch in enumerate(full_name):
            if ch.isupper():
                initial_indices.append(i)
        short_name = "".join(full_name[i] for i in initial_indices).lower()
        if short_name not in has:
            index[full_name] = short_name
            has[short_name] = True
            continue
        # Try appending last char
        if initial_indices[-1] != len(full_name) - 1:
            short_name2 = "".join(full_name[i] for i in initial_indices + [len(full_name) - 1]).lower()
            if short_name2 not in has:
                index[full_name] = short_name2
                has[short_name2] = True
                continue
        # Numeric suffix fallback
        n = 1
        while True:
            candidate = f"{short_name}_{n}"
            if candidate not in has:
                index[full_name] = candidate
                has[candidate] = True
                break
            n += 1
    return index


# Vega-Lite scale/axis/legend property lists (mirroring SCALE_PROPERTIES etc.)
SCALE_PROPERTIES: list[str] = [
    "align", "type", "domain", "domainMax", "domainMid", "domainMin",
    "base", "exponent", "constant", "bins", "clamp", "nice", "reverse",
    "round", "zero", "padding", "paddingInner", "paddingOuter",
    "interpolate", "range", "rangeMax", "rangeMin", "scheme",
]

AXIS_PROPERTIES: list[str] = [
    "aria", "description", "zindex", "offset", "orient", "values",
    "bandPosition", "encoding", "domain", "domainCap", "domainColor",
    "domainDash", "domainDashOffset", "domainOpacity", "domainWidth",
    "formatType", "grid", "gridCap", "gridColor", "gridDash",
    "gridDashOffset", "gridOpacity", "gridWidth", "format", "labels",
    "labelAlign", "labelAngle", "labelBaseline", "labelColor", "labelExpr",
    "labelFlushOffset", "labelFont", "labelFontSize", "labelFontStyle",
    "labelFontWeight", "labelLimit", "labelLineHeight", "labelOffset",
    "labelOpacity", "labelSeparation", "labelOverlap", "labelPadding",
    "labelBound", "labelFlush", "maxExtent", "minExtent", "position",
    "style", "ticks", "tickBand", "tickCap", "tickColor", "tickCount",
    "tickDash", "tickExtra", "tickDashOffset", "tickMinStep", "tickOffset",
    "tickOpacity", "tickRound", "tickSize", "tickWidth", "title",
    "titleAlign", "titleAnchor", "titleAngle", "titleBaseline", "titleColor",
    "titleFont", "titleFontSize", "titleFontStyle", "titleFontWeight",
    "titleLimit", "titleLineHeight", "titleOpacity", "titlePadding",
    "titleX", "titleY", "translate",
]

LEGEND_PROPERTIES: list[str] = [
    "aria", "description", "orient", "format", "type", "values", "zindex",
    "clipHeight", "columnPadding", "columns", "cornerRadius", "direction",
    "encoding", "fillColor", "formatType", "gridAlign", "offset", "padding",
    "rowPadding", "strokeColor", "labelAlign", "labelBaseline", "labelColor",
    "labelExpr", "labelFont", "labelFontSize", "labelFontStyle",
    "labelFontWeight", "labelLimit", "labelOffset", "labelOpacity",
    "labelOverlap", "labelPadding", "labelSeparation", "legendX", "legendY",
    "gradientLength", "gradientOpacity", "gradientStrokeColor",
    "gradientStrokeWidth", "gradientThickness", "symbolDash",
    "symbolDashOffset", "symbolFillColor", "symbolLimit", "symbolOffset",
    "symbolOpacity", "symbolSize", "symbolStrokeColor", "symbolStrokeWidth",
    "symbolType", "tickCount", "tickMinStep", "title", "titleAnchor",
    "titleAlign", "titleBaseline", "titleColor", "titleFont", "titleFontSize",
    "titleFontStyle", "titleFontWeight", "titleLimit", "titleLineHeight",
    "titleOpacity", "titleOrient", "titlePadding",
]

DEFAULT_NAME: dict[str, Any] = {
    "mark": "m",
    "channel": "c",
    "aggregate": "a",
    "autoCount": "#",
    "hasFn": "h",
    "bin": "b",
    "sort": "so",
    "stack": "st",
    "scale": "s",
    "format": "f",
    "axis": "ax",
    "legend": "l",
    "value": "v",
    "timeUnit": "tu",
    "field": "f",
    "type": "t",
    "binProps": {
        "maxbins": "mb",
        "min": "mi",
        "max": "ma",
        "base": "b",
        "step": "s",
        "steps": "ss",
        "minstep": "ms",
        "divide": "d",
    },
    "sortProps": {
        "field": "f",
        "op": "o",
        "order": "or",
    },
    "scaleProps": _init_nested_prop_name(SCALE_PROPERTIES),
    "axisProps": _init_nested_prop_name(AXIS_PROPERTIES),
    "legendProps": _init_nested_prop_name(LEGEND_PROPERTIES),
}

_DEFAULT_BOOLEAN_ENUM = [False, True]

DEFAULT_BIN_PROPS_ENUM: dict[str, list] = {
    "maxbins": [5, 10, 20],
    "extent": [None],
    "base": [10],
    "step": [None],
    "steps": [None],
    "minstep": [None],
    "divide": [[5, 2]],
    "binned": [False],
    "anchor": [None],
    "nice": [True],
}

DEFAULT_SORT_PROPS_ENUM: dict[str, list] = {
    "field": [None],
    "op": ["min", "mean"],
    "order": ["ascending", "descending"],
}

DEFAULT_SCALE_PROPS_ENUM: dict[str, list] = {
    "align": [None],
    "type": [None, "log"],
    "domain": [None],
    "domainMax": [None],
    "domainMid": [None],
    "domainMin": [None],
    "base": [None],
    "exponent": [1, 2],
    "constant": [None],
    "bins": [None],
    "clamp": _DEFAULT_BOOLEAN_ENUM,
    "nice": _DEFAULT_BOOLEAN_ENUM,
    "reverse": _DEFAULT_BOOLEAN_ENUM,
    "round": _DEFAULT_BOOLEAN_ENUM,
    "zero": _DEFAULT_BOOLEAN_ENUM,
    "padding": [None],
    "paddingInner": [None],
    "paddingOuter": [None],
    "interpolate": [None],
    "range": [None],
    "rangeMax": [None],
    "rangeMin": [None],
    "scheme": [None],
}

DEFAULT_AXIS_PROPS_ENUM: dict[str, list] = {
    "aria": [None],
    "description": [None],
    "zindex": [1, 0],
    "offset": [None],
    "orient": [None],
    "values": [None],
    "bandPosition": [None],
    "encoding": [None],
    "domain": _DEFAULT_BOOLEAN_ENUM,
    "domainCap": [None],
    "domainColor": [None],
    "domainDash": [None],
    "domainDashOffset": [None],
    "domainOpacity": [None],
    "domainWidth": [None],
    "formatType": [None],
    "grid": _DEFAULT_BOOLEAN_ENUM,
    "gridCap": [None],
    "gridColor": [None],
    "gridDash": [None],
    "gridDashOffset": [None],
    "gridOpacity": [None],
    "gridWidth": [None],
    "format": [None],
    "labels": _DEFAULT_BOOLEAN_ENUM,
    "labelAlign": [None],
    "labelAngle": [None],
    "labelBaseline": [None],
    "labelColor": [None],
    "labelExpr": [None],
    "labelFlushOffset": [None],
    "labelFont": [None],
    "labelFontSize": [None],
    "labelFontStyle": [None],
    "labelFontWeight": [None],
    "labelLimit": [None],
    "labelLineHeight": [None],
    "labelOffset": [None],
    "labelOpacity": [None],
    "labelSeparation": [None],
    "labelOverlap": [None],
    "labelPadding": [None],
    "labelBound": [None],
    "labelFlush": [None],
    "maxExtent": [None],
    "minExtent": [None],
    "position": [None],
    "style": [None],
    "ticks": _DEFAULT_BOOLEAN_ENUM,
    "tickBand": [None],
    "tickCap": [None],
    "tickColor": [None],
    "tickCount": [None],
    "tickDash": [None],
    "tickExtra": [None],
    "tickDashOffset": [None],
    "tickMinStep": [None],
    "tickOffset": [None],
    "tickOpacity": [None],
    "tickRound": [None],
    "tickSize": [None],
    "tickWidth": [None],
    "title": [None],
    "titleAlign": [None],
    "titleAnchor": [None],
    "titleAngle": [None],
    "titleBaseline": [None],
    "titleColor": [None],
    "titleFont": [None],
    "titleFontSize": [None],
    "titleFontStyle": [None],
    "titleFontWeight": [None],
    "titleLimit": [None],
    "titleLineHeight": [None],
    "titleOpacity": [None],
    "titlePadding": [None],
    "titleX": [None],
    "titleY": [None],
    "translate": [None],
}

DEFAULT_LEGEND_PROPS_ENUM: dict[str, list] = {
    "aria": [None],
    "description": [None],
    "orient": ["left", "right"],
    "format": [None],
    "type": [None],
    "values": [None],
    "zindex": [None],
    "clipHeight": [None],
    "columnPadding": [None],
    "columns": [None],
    "cornerRadius": [None],
    "direction": [None],
    "encoding": [None],
    "fillColor": [None],
    "formatType": [None],
    "gridAlign": [None],
    "offset": [None],
    "padding": [None],
    "rowPadding": [None],
    "strokeColor": [None],
    "labelAlign": [None],
    "labelBaseline": [None],
    "labelColor": [None],
    "labelExpr": [None],
    "labelFont": [None],
    "labelFontSize": [None],
    "labelFontStyle": [None],
    "labelFontWeight": [None],
    "labelLimit": [None],
    "labelOffset": [None],
    "labelOpacity": [None],
    "labelOverlap": [None],
    "labelPadding": [None],
    "labelSeparation": [None],
    "legendX": [None],
    "legendY": [None],
    "gradientLength": [None],
    "gradientOpacity": [None],
    "gradientStrokeColor": [None],
    "gradientStrokeWidth": [None],
    "gradientThickness": [None],
    "symbolDash": [None],
    "symbolDashOffset": [None],
    "symbolFillColor": [None],
    "symbolLimit": [None],
    "symbolOffset": [None],
    "symbolOpacity": [None],
    "symbolSize": [None],
    "symbolStrokeColor": [None],
    "symbolStrokeWidth": [None],
    "symbolType": [None],
    "tickCount": [None],
    "tickMinStep": [None],
    "title": [None],
    "titleAnchor": [None],
    "titleAlign": [None],
    "titleBaseline": [None],
    "titleColor": [None],
    "titleFont": [None],
    "titleFontSize": [None],
    "titleFontStyle": [None],
    "titleFontWeight": [None],
    "titleLimit": [None],
    "titleLineHeight": [None],
    "titleOpacity": [None],
    "titleOrient": [None],
    "titlePadding": [None],
}

DEFAULT_ENUM_INDEX: dict[str, Any] = {
    "mark": ["point", "bar", "line", "area", "rect", "tick", "text"],
    "channel": ["x", "y", "row", "column", "size", "color"],
    "band": [None],
    "aggregate": [None, "mean"],
    "autoCount": _DEFAULT_BOOLEAN_ENUM,
    "bin": _DEFAULT_BOOLEAN_ENUM,
    "hasFn": _DEFAULT_BOOLEAN_ENUM,
    "timeUnit": [None, "year", "month", "minutes", "seconds"],
    "field": [None],
    "type": ["nominal", "ordinal", "quantitative", "temporal"],
    "sort": ["ascending", "descending"],
    "stack": ["zero", "normalize", "center", None],
    "value": [None],
    "format": [None],
    "title": [None],
    "scale": [True],
    "axis": _DEFAULT_BOOLEAN_ENUM,
    "legend": _DEFAULT_BOOLEAN_ENUM,
    "binProps": DEFAULT_BIN_PROPS_ENUM,
    "sortProps": DEFAULT_SORT_PROPS_ENUM,
    "scaleProps": DEFAULT_SCALE_PROPS_ENUM,
    "axisProps": DEFAULT_AXIS_PROPS_ENUM,
    "legendProps": DEFAULT_LEGEND_PROPS_ENUM,
}


def get_default_name(prop: Any) -> str:
    """Return the short default wildcard name for a property."""
    from compassql.property import is_encoding_nested_prop
    if is_encoding_nested_prop(prop):
        parent_short = DEFAULT_NAME.get(prop.parent, prop.parent)
        parent_props_map = DEFAULT_NAME.get(f"{prop.parent}Props", {})
        child_short = parent_props_map.get(prop.child, prop.child)
        return f"{parent_short}-{child_short}"
    key = prop if isinstance(prop, str) else str(prop)
    if key in DEFAULT_NAME:
        val = DEFAULT_NAME[key]
        if isinstance(val, str):
            return val
    raise ValueError(f"Default name undefined for {prop}")


def get_default_enum_values(prop: Any, schema: Any, opt: Any) -> list:
    """Return the default enum values for a property given schema and config."""
    from compassql.property import is_encoding_nested_prop
    # field always enumerates all schema fields
    if prop == "field":
        return schema.field_names() if schema else []
    if is_encoding_nested_prop(prop):
        if prop.parent == "sort" and prop.child == "field":
            return schema.field_names() if schema else []
        enum_cfg = opt.enum if opt and opt.enum else DEFAULT_ENUM_INDEX
        props_key = f"{prop.parent}Props"
        parent_enum = enum_cfg.get(props_key, {})
        val = parent_enum.get(prop.child)
        if val is not None:
            return val
        raise ValueError(f"No default enumValues for {prop}")
    enum_cfg = opt.enum if opt and opt.enum else DEFAULT_ENUM_INDEX
    val = enum_cfg.get(prop if isinstance(prop, str) else str(prop))
    if val is not None:
        return val
    raise ValueError(f"No default enumValues for {prop}")
