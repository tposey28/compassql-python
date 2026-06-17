from __future__ import annotations

from typing import Any

from compassql.config import QueryConfig
from compassql.query.encoding import is_field_query
from compassql.schema import Schema, ExpandedType


def _scale_type(enc_q: Any) -> str | None:
    """Infer the Vega-Lite scale type for an encoding query."""
    scale = getattr(enc_q, "scale", None)
    if isinstance(scale, dict) and scale.get("type"):
        return scale["type"]
    field_type = getattr(enc_q, "type", None)
    bin_val = getattr(enc_q, "bin", None)
    time_unit = getattr(enc_q, "timeUnit", None)
    if bin_val:
        return "bin-ordinal"
    if time_unit:
        return "time"
    if field_type in ("ordinal", "nominal", "key"):
        return "ordinal"
    if field_type == "temporal":
        return "time"
    if field_type == "quantitative":
        return "linear"
    return None


def _has_discrete_domain(scale_type_str: str | None) -> bool:
    """Return True if this scale type has a discrete domain."""
    return scale_type_str in ("ordinal", "band", "point", "bin-ordinal", None)


def _enc_get(enc_q: Any, attr: str) -> Any:
    return getattr(enc_q, attr, None)


def _enc_set(enc_q: Any, attr: str, value: Any) -> None:
    setattr(enc_q, attr, value)


def stylize(answer_set: list, schema: Schema, opt: QueryConfig) -> list:
    """Apply heuristic style transformations to each SpecQueryModel in the answer set."""
    enc_q_index: dict[str, Any] = {}
    result = []
    for spec_m in answer_set:
        if opt.small_range_step_for_high_cardinality_or_facet:
            spec_m = _small_range_step(spec_m, schema, enc_q_index, opt)
        if opt.nominal_color_scale_for_high_cardinality:
            spec_m = _nominal_color_scale(spec_m, schema, enc_q_index, opt)
        if opt.x_axis_on_top_for_high_y_cardinality_without_column:
            spec_m = _x_axis_on_top(spec_m, schema, enc_q_index, opt)
        result.append(spec_m)
    return result


def _small_range_step(spec_m: Any, schema: Schema, enc_q_index: dict, opt: QueryConfig) -> Any:
    for ch in ("row", "y", "column", "x"):
        enc_q_index[ch] = spec_m.get_encoding_query_by_channel(ch)

    y_enc_q = enc_q_index.get("y")
    if y_enc_q is not None and is_field_query(y_enc_q):
        has_row = enc_q_index.get("row") is not None
        cardinality = schema.cardinality(vars(y_enc_q))
        max_card = opt.small_range_step_for_high_cardinality_or_facet["maxCardinality"]
        range_step = opt.small_range_step_for_high_cardinality_or_facet["rangeStep"]
        if has_row or (cardinality is not None and cardinality > max_card):
            scale = _enc_get(y_enc_q, "scale")
            if scale is None:
                _enc_set(y_enc_q, "scale", {})
                scale = _enc_get(y_enc_q, "scale")
            y_scale_type = _scale_type(y_enc_q)
            if scale is not False and (y_scale_type is None or _has_discrete_domain(y_scale_type)):
                if not spec_m.spec_query.height:
                    spec_m.spec_query.height = {"step": range_step}

    x_enc_q = enc_q_index.get("x")
    if x_enc_q is not None and is_field_query(x_enc_q):
        has_col = enc_q_index.get("column") is not None
        cardinality = schema.cardinality(vars(x_enc_q))
        max_card = opt.small_range_step_for_high_cardinality_or_facet["maxCardinality"]
        range_step = opt.small_range_step_for_high_cardinality_or_facet["rangeStep"]
        if has_col or (cardinality is not None and cardinality > max_card):
            scale = _enc_get(x_enc_q, "scale")
            if scale is None:
                _enc_set(x_enc_q, "scale", {})
                scale = _enc_get(x_enc_q, "scale")
            x_scale_type = _scale_type(x_enc_q)
            if scale is not False and (x_scale_type is None or _has_discrete_domain(x_scale_type)):
                if not spec_m.spec_query.width:
                    spec_m.spec_query.width = {"step": range_step}

    return spec_m


def _nominal_color_scale(spec_m: Any, schema: Schema, enc_q_index: dict, opt: QueryConfig) -> Any:
    enc_q_index["color"] = spec_m.get_encoding_query_by_channel("color")
    color_enc_q = enc_q_index.get("color")

    if color_enc_q is not None and is_field_query(color_enc_q):
        field_type = _enc_get(color_enc_q, "type")
        if field_type in ("nominal", "key"):
            cardinality = schema.cardinality(vars(color_enc_q))
            max_card = opt.nominal_color_scale_for_high_cardinality["maxCardinality"]
            palette = opt.nominal_color_scale_for_high_cardinality["palette"]
            if cardinality is not None and cardinality > max_card:
                scale = _enc_get(color_enc_q, "scale")
                if scale is None:
                    _enc_set(color_enc_q, "scale", {})
                    scale = _enc_get(color_enc_q, "scale")
                if scale and isinstance(scale, dict) and not scale.get("range"):
                    scale["scheme"] = palette

    return spec_m


def _x_axis_on_top(spec_m: Any, schema: Schema, enc_q_index: dict, opt: QueryConfig) -> Any:
    for ch in ("column", "x", "y"):
        enc_q_index[ch] = spec_m.get_encoding_query_by_channel(ch)

    if enc_q_index.get("column") is None:
        x_enc_q = enc_q_index.get("x")
        y_enc_q = enc_q_index.get("y")

        if (
            x_enc_q is not None
            and y_enc_q is not None
            and is_field_query(x_enc_q)
            and is_field_query(y_enc_q)
            and _enc_get(y_enc_q, "field")
            and _has_discrete_domain(_scale_type(y_enc_q))
        ):
            cardinality = schema.cardinality(
                vars(y_enc_q)
            )
            max_card = opt.x_axis_on_top_for_high_y_cardinality_without_column["maxCardinality"]
            if cardinality is not None and cardinality > max_card:
                axis = _enc_get(x_enc_q, "axis")
                if axis is None:
                    _enc_set(x_enc_q, "axis", {})
                    axis = _enc_get(x_enc_q, "axis")
                if axis and isinstance(axis, dict) and not axis.get("orient"):
                    axis["orient"] = "top"

    return spec_m
