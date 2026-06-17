"""Spec-level constraints for CompassQL (ported from src/constraint/spec.ts)."""
from __future__ import annotations

from typing import Callable, Optional, Any

from compassql.constraint.base import AbstractConstraint, AbstractConstraintModel
from compassql.property import (
    Property,
    is_encoding_property,
    is_encoding_nested_prop,
    get_encoding_nested_prop,
)
from compassql.propindex import PropIndex
from compassql.wildcard import is_wildcard
from compassql.query.encoding import (
    is_auto_count_query,
    is_disabled_auto_count_query,
    is_enabled_auto_count_query,
    is_field_query,
    is_value_query,
    is_dimension,
    is_measure,
)
from compassql.vegalite_types import (
    Mark,
    Channel,
    SUM_OPS,
    NONPOSITION_CHANNELS,
    support_mark,
    ScaleType,
)


# ---------------------------------------------------------------------------
# SpecConstraintModel
# ---------------------------------------------------------------------------

SpecConstraintChecker = Callable[..., bool]


class SpecConstraintModel(AbstractConstraintModel):
    def __init__(self, constraint: AbstractConstraint, checker: SpecConstraintChecker):
        super().__init__(constraint)
        self._checker = checker

    def has_all_required_properties_specific(self, spec_m) -> bool:
        for prop in self._c.properties:
            if prop == Property.MARK or prop == "mark":
                if is_wildcard(spec_m.get_mark()):
                    return False
            elif is_encoding_nested_prop(prop):
                parent = prop.parent
                child = prop.child
                for enc_q in spec_m.get_encodings():
                    parent_val = _enc_attr(enc_q, parent)
                    if parent_val and isinstance(parent_val, dict):
                        if is_wildcard(parent_val.get(child)):
                            return False
            elif is_encoding_property(prop):
                for enc_q in spec_m.get_encodings():
                    val = _enc_attr(enc_q, prop)
                    if val is not None and is_wildcard(val):
                        return False
        return True

    def satisfy(self, spec_m, schema, opt) -> bool:
        if not self._c.allow_wildcard_for_properties:
            if not self.has_all_required_properties_specific(spec_m):
                return True
        return self._checker(spec_m, schema, opt)


def _enc_attr(enc_q: Any, prop) -> Any:
    key = prop if isinstance(prop, str) else str(prop)
    return getattr(enc_q, key, None)


def _make(name_, description, properties, allow_wildcard, strict_, checker) -> SpecConstraintModel:
    c = AbstractConstraint(
        name_=name_,
        description=description,
        properties=properties,
        allow_wildcard_for_properties=allow_wildcard,
        strict_=strict_,
    )
    return SpecConstraintModel(c, checker)


# ---------------------------------------------------------------------------
# Non-positional channel index
# ---------------------------------------------------------------------------

_NONPOSITION_CHANNELS_INDEX: set[str] = {str(ch) for ch in NONPOSITION_CHANNELS}


# ---------------------------------------------------------------------------
# Constraint definitions (same order as spec.ts)
# ---------------------------------------------------------------------------

def _no_repeated_channel(spec_m, schema, opt) -> bool:
    used: dict[str, bool] = {}
    for enc_q in spec_m.get_encodings():
        ch = _enc_attr(enc_q, "channel")
        if not is_wildcard(ch):
            if used.get(str(ch)):
                return False
            used[str(ch)] = True
    return True


def _mark_eq(mark, mark_enum_val) -> bool:
    """Compare a mark value (str or enum) against a Mark enum member."""
    if mark is None:
        return False
    if mark == mark_enum_val:
        return True
    mark_str = mark.value if hasattr(mark, "value") else str(mark)
    enum_str = mark_enum_val.value if hasattr(mark_enum_val, "value") else str(mark_enum_val)
    return mark_str == enum_str


def _channel_eq(ch, ch_str: str) -> bool:
    """Compare a channel value (str or enum) against a plain string."""
    if ch is None:
        return False
    if ch == ch_str:
        return True
    return (ch.value if hasattr(ch, "value") else str(ch)) == ch_str


def _always_include_zero_in_scale_with_bar(spec_m, schema, opt) -> bool:
    mark = spec_m.get_mark()
    if _mark_eq(mark, Mark.BAR):
        for enc_q in spec_m.get_encodings():
            if not is_field_query(enc_q):
                continue
            ch = _enc_attr(enc_q, "channel")
            if not (_channel_eq(ch, "x") or _channel_eq(ch, "y")):
                continue
            if _enc_attr(enc_q, "type") not in ("quantitative",):
                continue
            scale = _enc_attr(enc_q, "scale")
            if isinstance(scale, dict) and scale.get("zero") is False:
                return False
    return True


def _auto_add_count(spec_m, schema, opt) -> bool:
    from compassql.query.expandedtype import ExpandedType
    has_auto_count = any(is_enabled_auto_count_query(e) for e in spec_m.get_encodings())

    if has_auto_count:
        for enc_q in spec_m.get_encodings():
            if is_value_query(enc_q):
                continue
            if is_auto_count_query(enc_q):
                continue
            t = _enc_attr(enc_q, "type")
            if t == "quantitative":
                if not _enc_attr(enc_q, "bin"):
                    return False
            elif t == "temporal":
                if not _enc_attr(enc_q, "timeUnit"):
                    return False
            elif t in ("ordinal", "nominal", ExpandedType.KEY, "key"):
                continue
            else:
                raise ValueError(f"Unsupported type: {t}")
        return True
    else:
        auto_count_indices = spec_m.wildcard_index.encoding_indices_by_property.get("autoCount") or []
        never_have_auto_count = all(
            is_auto_count_query(spec_m.get_encoding_query_by_index(i)) and
            not is_wildcard(_enc_attr(spec_m.get_encoding_query_by_index(i), "autoCount"))
            for i in auto_count_indices
        )
        if never_have_auto_count:
            return any(
                (
                    (is_field_query(e) or is_auto_count_query(e)) and
                    _enc_attr(e, "type") == "quantitative" and
                    not is_disabled_auto_count_query(e) and
                    is_field_query(e) and
                    (not _enc_attr(e, "bin") or is_wildcard(_enc_attr(e, "bin")))
                ) or (
                    is_field_query(e) and
                    _enc_attr(e, "type") == "temporal" and
                    (not _enc_attr(e, "timeUnit") or is_wildcard(_enc_attr(e, "timeUnit")))
                )
                for e in spec_m.get_encodings()
            )
    return True


def _channel_permitted_by_mark_type(spec_m, schema, opt) -> bool:
    mark = spec_m.get_mark()
    if is_wildcard(mark):
        return True
    for enc_q in spec_m.get_encodings():
        ch = _enc_attr(enc_q, "channel")
        if is_wildcard(ch):
            continue
        ch_str = str(ch)
        if ch_str in ("row", "column", "facet"):
            continue
        if not support_mark(ch_str, str(mark)):
            return False
    return True


def _has_all_required_channels_for_mark(spec_m, schema, opt) -> bool:
    mark = str(spec_m.get_mark())
    x_used = spec_m.channel_used("x")
    y_used = spec_m.channel_used("y")

    if mark in (str(Mark.AREA), str(Mark.LINE), "area", "line"):
        return x_used and y_used
    if mark in (str(Mark.TEXT), "text"):
        return spec_m.channel_used("text")
    if mark in (str(Mark.BAR), str(Mark.CIRCLE), str(Mark.SQUARE), str(Mark.TICK), str(Mark.RULE), str(Mark.RECT),
                "bar", "circle", "square", "tick", "rule", "rect"):
        return x_used or y_used
    if mark in (str(Mark.POINT), "point"):
        return (
            not spec_m.wildcard_index.has_property(Property.CHANNEL) or
            x_used or y_used
        )
    raise ValueError(f"hasAllRequiredChannelsForMark not implemented for mark {mark}")


def _omit_aggregate(spec_m, schema, opt) -> bool:
    return not spec_m.is_aggregate()


def _omit_aggregate_plot_with_dimension_only_on_facet(spec_m, schema, opt) -> bool:
    if spec_m.is_aggregate():
        has_non_facet_dim = False
        has_dim = False
        has_enumerated_facet_dim = False
        encodings = spec_m.spec_query.get("encodings", []) if isinstance(spec_m.spec_query, dict) else spec_m.spec_query.encodings
        for index, enc_q in enumerate(encodings):
            if is_value_query(enc_q) or is_disabled_auto_count_query(enc_q):
                continue
            if is_field_query(enc_q) and not _enc_attr(enc_q, "aggregate"):
                has_dim = True
                ch = str(_enc_attr(enc_q, "channel") or "")
                if ch in ("row", "column"):
                    if spec_m.wildcard_index.has_encoding_property(index, Property.CHANNEL):
                        has_enumerated_facet_dim = True
                else:
                    has_non_facet_dim = True
        if has_dim and not has_non_facet_dim:
            if has_enumerated_facet_dim or getattr(opt, "constraint_manually_specified_value", False):
                return False
    return True


def _omit_aggregate_plot_without_dimension(spec_m, schema, opt) -> bool:
    if spec_m.is_aggregate():
        return any(
            is_dimension(e) or (is_field_query(e) and _enc_attr(e, "type") == "temporal")
            for e in spec_m.get_encodings()
        )
    return True


def _omit_bar_line_area_with_occlusion(spec_m, schema, opt) -> bool:
    mark = str(spec_m.get_mark())
    if mark in (str(Mark.BAR), str(Mark.LINE), str(Mark.AREA), "bar", "line", "area"):
        return spec_m.is_aggregate()
    return True


def _omit_bar_tick_with_size(spec_m, schema, opt) -> bool:
    mark = str(spec_m.get_mark())
    if mark in (str(Mark.TICK), str(Mark.BAR), "tick", "bar"):
        if spec_m.channel_encoding_field("size"):
            if getattr(opt, "constraint_manually_specified_value", False):
                return False
            else:
                encodings = spec_m.spec_query.get("encodings", []) if isinstance(spec_m.spec_query, dict) else spec_m.spec_query.encodings
                for i, enc_q in enumerate(encodings):
                    if str(_enc_attr(enc_q, "channel") or "") == "size":
                        if spec_m.wildcard_index.has_encoding_property(i, Property.CHANNEL):
                            return False
                        else:
                            return True
    return True


def _omit_bar_area_for_log_scale(spec_m, schema, opt) -> bool:
    mark = str(spec_m.get_mark())
    if mark in (str(Mark.AREA), str(Mark.BAR), "area", "bar"):
        for enc_q in spec_m.get_encodings():
            if not is_field_query(enc_q):
                continue
            ch = str(_enc_attr(enc_q, "channel") or "")
            if ch not in ("x", "y"):
                continue
            scale = _enc_attr(enc_q, "scale")
            if not scale:
                continue
            # Check if scale type resolves to log
            scale_type_val = scale.get("type") if isinstance(scale, dict) else None
            if scale_type_val == "log" or scale_type_val == str(ScaleType.LOG):
                return False
    return True


def _omit_multiple_non_positional_channels(spec_m, schema, opt) -> bool:
    encodings = spec_m.spec_query.get("encodings", []) if isinstance(spec_m.spec_query, dict) else spec_m.spec_query.encodings
    non_pos_count = 0
    has_enumerated_non_pos = False
    for i, enc_q in enumerate(encodings):
        if is_value_query(enc_q) or is_disabled_auto_count_query(enc_q):
            continue
        ch = _enc_attr(enc_q, "channel")
        if not is_wildcard(ch):
            if str(ch) in _NONPOSITION_CHANNELS_INDEX:
                non_pos_count += 1
                if spec_m.wildcard_index.has_encoding_property(i, Property.CHANNEL):
                    has_enumerated_non_pos = True
                if non_pos_count > 1 and (has_enumerated_non_pos or getattr(opt, "constraint_manually_specified_value", False)):
                    return False
    return True


def _omit_non_positional_or_facet_over_positional(spec_m, schema, opt) -> bool:
    encodings = spec_m.spec_query.get("encodings", []) if isinstance(spec_m.spec_query, dict) else spec_m.spec_query.encodings
    has_non_pos_or_facet = False
    has_enumerated_non_pos_or_facet = False
    has_x = False
    has_y = False
    for i, enc_q in enumerate(encodings):
        if is_value_query(enc_q) or is_disabled_auto_count_query(enc_q):
            continue
        ch = _enc_attr(enc_q, "channel")
        ch_str = str(ch) if ch is not None else ""
        if ch_str == "x":
            has_x = True
        elif ch_str == "y":
            has_y = True
        elif not is_wildcard(ch):
            has_non_pos_or_facet = True
            if spec_m.wildcard_index.has_encoding_property(i, Property.CHANNEL):
                has_enumerated_non_pos_or_facet = True
    if has_enumerated_non_pos_or_facet or (getattr(opt, "constraint_manually_specified_value", False) and has_non_pos_or_facet):
        return has_x and has_y
    return True


def _omit_raw(spec_m, schema, opt) -> bool:
    return spec_m.is_aggregate()


def _omit_raw_continuous_field_for_aggregate_plot(spec_m, schema, opt) -> bool:
    if spec_m.is_aggregate():
        encodings = spec_m.spec_query.get("encodings", []) if isinstance(spec_m.spec_query, dict) else spec_m.spec_query.encodings
        for i, enc_q in enumerate(encodings):
            if is_value_query(enc_q) or is_disabled_auto_count_query(enc_q):
                continue
            t = _enc_attr(enc_q, "type")
            if is_field_query(enc_q) and t == "temporal":
                if not _enc_attr(enc_q, "timeUnit"):
                    if spec_m.wildcard_index.has_encoding_property(i, Property.TIMEUNIT) or getattr(opt, "constraint_manually_specified_value", False):
                        return False
            if t == "quantitative":
                if is_field_query(enc_q) and not _enc_attr(enc_q, "bin") and not _enc_attr(enc_q, "aggregate"):
                    if (
                        spec_m.wildcard_index.has_encoding_property(i, Property.BIN) or
                        spec_m.wildcard_index.has_encoding_property(i, Property.AGGREGATE) or
                        spec_m.wildcard_index.has_encoding_property(i, "autoCount")
                    ):
                        return False
                    if getattr(opt, "constraint_manually_specified_value", False):
                        return False
    return True


def _omit_raw_detail(spec_m, schema, opt) -> bool:
    if spec_m.is_aggregate():
        return True
    encodings = spec_m.spec_query.get("encodings", []) if isinstance(spec_m.spec_query, dict) else spec_m.spec_query.encodings
    for i, enc_q in enumerate(encodings):
        if is_value_query(enc_q) or is_disabled_auto_count_query(enc_q):
            continue
        if str(_enc_attr(enc_q, "channel") or "") == "detail":
            if spec_m.wildcard_index.has_encoding_property(i, Property.CHANNEL) or getattr(opt, "constraint_manually_specified_value", False):
                return False
    return True


def _omit_repeated_field(spec_m, schema, opt) -> bool:
    field_used: dict[str, bool] = {}
    field_enumerated: dict[str, bool] = {}
    encodings = spec_m.spec_query.get("encodings", []) if isinstance(spec_m.spec_query, dict) else spec_m.spec_query.encodings
    for i, enc_q in enumerate(encodings):
        if is_value_query(enc_q) or is_auto_count_query(enc_q):
            continue
        fld = None
        f_val = _enc_attr(enc_q, "field")
        if f_val and not is_wildcard(f_val):
            fld = str(f_val)
        if fld:
            if spec_m.wildcard_index.has_encoding_property(i, Property.FIELD):
                field_enumerated[fld] = True
            if field_used.get(fld):
                if field_enumerated.get(fld) or getattr(opt, "constraint_manually_specified_value", False):
                    return False
            field_used[fld] = True
    return True


def _omit_vertical_dot_plot(spec_m, schema, opt) -> bool:
    encodings = spec_m.get_encodings()
    if len(encodings) == 1 and str(_enc_attr(encodings[0], "channel") or "") == "y":
        return False
    return True


def _has_appropriate_graphic_type_for_mark(spec_m, schema, opt) -> bool:
    mark = str(spec_m.get_mark())

    if mark in (str(Mark.AREA), str(Mark.LINE), "area", "line"):
        if spec_m.is_aggregate():
            x_enc = spec_m.get_encoding_query_by_channel("x")
            y_enc = spec_m.get_encoding_query_by_channel("y")
            x_is_measure = is_measure(x_enc) if x_enc is not None else False
            y_is_measure = is_measure(y_enc) if y_enc is not None else False
            if not (x_enc and y_enc and (x_is_measure != y_is_measure)):
                return False
            # Dimension axis should not be nominal
            if is_field_query(x_enc) and not x_is_measure and _enc_attr(x_enc, "type") in ("nominal", "key"):
                return False
            if is_field_query(y_enc) and not y_is_measure and _enc_attr(y_enc, "type") in ("nominal", "key"):
                return False
            return True
        return True

    if mark in (str(Mark.TEXT), "text"):
        return True

    if mark in (str(Mark.BAR), str(Mark.TICK), "bar", "tick"):
        if spec_m.channel_encoding_field("size"):
            return False
        x_enc = spec_m.get_encoding_query_by_channel("x")
        y_enc = spec_m.get_encoding_query_by_channel("y")
        x_is_measure = is_measure(x_enc) if x_enc is not None else False
        y_is_measure = is_measure(y_enc) if y_enc is not None else False
        return x_is_measure != y_is_measure

    if mark in (str(Mark.RECT), "rect"):
        x_enc = spec_m.get_encoding_query_by_channel("x")
        y_enc = spec_m.get_encoding_query_by_channel("y")
        x_is_dim = is_dimension(x_enc) if x_enc is not None else False
        y_is_dim = is_dimension(y_enc) if y_enc is not None else False
        color_enc = spec_m.get_encoding_query_by_channel("color")
        color_is_q = is_measure(color_enc) if color_enc is not None else False
        color_is_ord = (is_field_query(color_enc) and _enc_attr(color_enc, "type") == "ordinal") if color_enc is not None else False
        correct_channels = (
            (x_is_dim and y_is_dim) or
            (x_is_dim and not spec_m.channel_used("y")) or
            (y_is_dim and not spec_m.channel_used("x"))
        )
        correct_color = not color_enc or (color_is_q or color_is_ord)
        return correct_channels and correct_color

    if mark in (str(Mark.CIRCLE), str(Mark.POINT), str(Mark.SQUARE), str(Mark.RULE),
                "circle", "point", "square", "rule"):
        return True

    raise ValueError(f"hasAppropriateGraphicTypeForMark not implemented for mark {mark}")


def _omit_invalid_stack_spec(spec_m, schema, opt) -> bool:
    if not spec_m.wildcard_index.has_property(Property.STACK):
        return True
    stack_props = _get_vl_stack(spec_m)
    if stack_props is None and spec_m.get_stack_offset() is not None:
        return False
    if stack_props and stack_props.get("fieldChannel") != spec_m.get_stack_channel():
        return False
    return True


def _omit_non_sum_stack(spec_m, schema, opt) -> bool:
    stack_props = _get_vl_stack(spec_m)
    if stack_props is not None:
        field_channel = stack_props.get("fieldChannel")
        enc_q = spec_m.get_encoding_query_by_channel(field_channel) if field_channel else None
        if enc_q is not None and is_field_query(enc_q):
            agg = _enc_attr(enc_q, "aggregate")
            if agg not in SUM_OPS:
                return False
    return True


def _omit_table_with_occlusion_if_auto_add_count(spec_m, schema, opt) -> bool:
    if getattr(opt, "auto_add_count", False):
        x_enc = spec_m.get_encoding_query_by_channel("x")
        y_enc = spec_m.get_encoding_query_by_channel("y")
        x_is_dim = not is_field_query(x_enc) or is_dimension(x_enc) if x_enc is not None else True
        y_is_dim = not is_field_query(y_enc) or is_dimension(y_enc) if y_enc is not None else True
        if x_is_dim and y_is_dim:
            if not spec_m.is_aggregate():
                return False
            else:
                for enc_q in spec_m.get_encodings():
                    ch = str(_enc_attr(enc_q, "channel") or "")
                    if ch not in ("x", "y", "row", "column"):
                        if is_field_query(enc_q) and not _enc_attr(enc_q, "aggregate"):
                            return False
    return True


def _get_vl_stack(spec_m) -> Optional[dict]:
    """Minimal helper to derive stack properties from a SpecQueryModel."""
    mark = str(spec_m.get_mark())
    if mark not in ("bar", "area", str(Mark.BAR), str(Mark.AREA)):
        return None
    for enc_q in spec_m.get_encodings():
        ch = str(_enc_attr(enc_q, "channel") or "")
        if ch in ("x", "y") and is_field_query(enc_q):
            agg = _enc_attr(enc_q, "aggregate")
            t = _enc_attr(enc_q, "type")
            if t == "quantitative" and agg:
                return {"fieldChannel": ch}
    return None


# ---------------------------------------------------------------------------
# SPEC_CONSTRAINTS list
# ---------------------------------------------------------------------------

SPEC_CONSTRAINTS: list[SpecConstraintModel] = [
    _make(
        "noRepeatedChannel",
        "Each encoding channel should only be used once.",
        [Property.CHANNEL],
        True, True,
        _no_repeated_channel,
    ),
    _make(
        "alwaysIncludeZeroInScaleWithBarMark",
        "Do not recommend bar mark if scale does not start at zero",
        [
            Property.MARK,
            Property.SCALE,
            get_encoding_nested_prop("scale", "zero"),
            Property.CHANNEL,
            Property.TYPE,
        ],
        False, True,
        _always_include_zero_in_scale_with_bar,
    ),
    _make(
        "autoAddCount",
        "Automatically adding count only for plots with only ordinal, binned quantitative, or temporal with timeunit fields.",
        [Property.BIN, Property.TIMEUNIT, Property.TYPE, Property.AUTOCOUNT],
        True, False,
        _auto_add_count,
    ),
    _make(
        "channelPermittedByMarkType",
        "Each encoding channel should be supported by the mark type",
        [Property.CHANNEL, Property.MARK],
        True, True,
        _channel_permitted_by_mark_type,
    ),
    _make(
        "hasAllRequiredChannelsForMark",
        "All required channels for the specified mark should be specified",
        [Property.CHANNEL, Property.MARK],
        False, True,
        _has_all_required_channels_for_mark,
    ),
    _make(
        "omitAggregate",
        "Omit aggregate plots.",
        [Property.AGGREGATE, Property.AUTOCOUNT],
        True, False,
        _omit_aggregate,
    ),
    _make(
        "omitAggregatePlotWithDimensionOnlyOnFacet",
        "Omit aggregate plots with dimensions only on facets as that leads to inefficient use of space.",
        [Property.CHANNEL, Property.AGGREGATE, Property.AUTOCOUNT],
        False, False,
        _omit_aggregate_plot_with_dimension_only_on_facet,
    ),
    _make(
        "omitAggregatePlotWithoutDimension",
        "Aggregate plots without dimension should be omitted",
        [Property.AGGREGATE, Property.AUTOCOUNT, Property.BIN, Property.TIMEUNIT, Property.TYPE],
        False, False,
        _omit_aggregate_plot_without_dimension,
    ),
    _make(
        "omitBarLineAreaWithOcclusion",
        "Don't use bar, line or area to visualize raw plot as they often lead to occlusion.",
        [Property.MARK, Property.AGGREGATE, Property.AUTOCOUNT],
        False, False,
        _omit_bar_line_area_with_occlusion,
    ),
    _make(
        "omitBarTickWithSize",
        "Do not map field to size channel with bar and tick mark",
        [Property.CHANNEL, Property.MARK],
        True, False,
        _omit_bar_tick_with_size,
    ),
    _make(
        "omitBarAreaForLogScale",
        "Do not use bar and area mark for x and y's log scale",
        [
            Property.MARK,
            Property.CHANNEL,
            Property.SCALE,
            get_encoding_nested_prop("scale", "type"),
            Property.TYPE,
        ],
        False, True,
        _omit_bar_area_for_log_scale,
    ),
    _make(
        "omitMultipleNonPositionalChannels",
        "Unless manually specified, do not use multiple non-positional encoding channel to avoid over-encoding.",
        [Property.CHANNEL],
        True, False,
        _omit_multiple_non_positional_channels,
    ),
    _make(
        "omitNonPositionalOrFacetOverPositionalChannels",
        "Do not use non-positional channels unless all positional channels are used",
        [Property.CHANNEL],
        False, False,
        _omit_non_positional_or_facet_over_positional,
    ),
    _make(
        "omitRaw",
        "Omit raw plots.",
        [Property.AGGREGATE, Property.AUTOCOUNT],
        False, False,
        _omit_raw,
    ),
    _make(
        "omitRawContinuousFieldForAggregatePlot",
        "Aggregate plot should not use raw continuous field as group by values.",
        [Property.AGGREGATE, Property.AUTOCOUNT, Property.TIMEUNIT, Property.BIN, Property.TYPE],
        True, False,
        _omit_raw_continuous_field_for_aggregate_plot,
    ),
    _make(
        "omitRawDetail",
        "Do not use detail channel with raw plot.",
        [Property.CHANNEL, Property.AGGREGATE, Property.AUTOCOUNT],
        False, True,
        _omit_raw_detail,
    ),
    _make(
        "omitRepeatedField",
        "Each field should be mapped to only one channel",
        [Property.FIELD],
        True, False,
        _omit_repeated_field,
    ),
    _make(
        "omitVerticalDotPlot",
        "Do not output vertical dot plot.",
        [Property.CHANNEL],
        True, False,
        _omit_vertical_dot_plot,
    ),
    # EXPENSIVE CONSTRAINTS
    _make(
        "hasAppropriateGraphicTypeForMark",
        "Has appropriate graphic type for mark",
        [
            Property.CHANNEL,
            Property.MARK,
            Property.TYPE,
            Property.TIMEUNIT,
            Property.BIN,
            Property.AGGREGATE,
            Property.AUTOCOUNT,
        ],
        False, False,
        _has_appropriate_graphic_type_for_mark,
    ),
    _make(
        "omitInvalidStackSpec",
        "If stack is specified, must follow Vega-Lite stack rules",
        [
            Property.STACK,
            Property.FIELD,
            Property.CHANNEL,
            Property.MARK,
            Property.AGGREGATE,
            Property.AUTOCOUNT,
            Property.SCALE,
            get_encoding_nested_prop("scale", "type"),
            Property.TYPE,
        ],
        False, True,
        _omit_invalid_stack_spec,
    ),
    _make(
        "omitNonSumStack",
        "Stack specifications that use non-summative aggregates should be omitted (even implicit ones)",
        [
            Property.CHANNEL,
            Property.MARK,
            Property.AGGREGATE,
            Property.AUTOCOUNT,
            Property.SCALE,
            get_encoding_nested_prop("scale", "type"),
            Property.TYPE,
        ],
        False, True,
        _omit_non_sum_stack,
    ),
    _make(
        "omitTableWithOcclusionIfAutoAddCount",
        "Plots without aggregation or autocount where x and y are both discrete should be omitted if autoAddCount is enabled",
        [
            Property.CHANNEL,
            Property.TYPE,
            Property.TIMEUNIT,
            Property.BIN,
            Property.AGGREGATE,
            Property.AUTOCOUNT,
        ],
        False, False,
        _omit_table_with_occlusion_if_auto_add_count,
    ),
]

# For testing – index by name
SPEC_CONSTRAINT_INDEX: dict[str, SpecConstraintModel] = {c.name(): c for c in SPEC_CONSTRAINTS}

# Property → constraints index
SPEC_CONSTRAINTS_BY_PROPERTY: PropIndex[list[SpecConstraintModel]] = PropIndex()
for _c in SPEC_CONSTRAINTS:
    for _prop in _c.properties():
        _existing = SPEC_CONSTRAINTS_BY_PROPERTY.get(_prop) or []
        SPEC_CONSTRAINTS_BY_PROPERTY.set(_prop, _existing + [_c])


# ---------------------------------------------------------------------------
# checkSpec
# ---------------------------------------------------------------------------

def check_spec(prop, wildcard, spec_m, schema, opt) -> Optional[str]:
    """Check all spec constraints for a property during enumeration.
    Returns the name of the violated constraint, or None if all pass.
    """
    constraints = SPEC_CONSTRAINTS_BY_PROPERTY.get(prop) or []
    for c in constraints:
        if c.strict() or bool(getattr(opt, c.name(), False)):
            if not c.satisfy(spec_m, schema, opt):
                violated = f"(spec) {c.name()}"
                if getattr(opt, "verbose", False):
                    wc_name = wildcard.name if hasattr(wildcard, "name") else str(wildcard)
                    print(f"{violated} failed with {spec_m.to_shorthand()} for {wc_name}")
                return violated
    return None
