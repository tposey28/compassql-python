from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from compassql.property import DEFAULT_PROP_PRECEDENCE, to_key
from compassql.wildcard import DEFAULT_ENUM_INDEX


@dataclass
class QueryConfig:
    verbose: bool = False
    default_spec_config: Optional[dict] = None
    property_precedence: Optional[list[str]] = None
    enum: Optional[dict] = None

    number_nominal_proportion: float = 0.05
    number_nominal_limit: int = 40

    # CONSTRAINTS
    constraint_manually_specified_value: bool = False
    auto_add_count: bool = False

    # Spec constraints
    has_appropriate_graphic_type_for_mark: bool = True
    omit_aggregate: bool = False
    omit_aggregate_plot_with_dimension_only_on_facet: bool = True
    omit_aggregate_plot_without_dimension: bool = False
    omit_bar_line_area_with_occlusion: bool = True
    omit_bar_tick_with_size: bool = True
    omit_multiple_non_positional_channels: bool = True
    omit_raw: bool = False
    omit_raw_continuous_field_for_aggregate_plot: bool = True
    omit_raw_with_xy_both_ordinal_scale_or_bin: bool = False
    omit_repeated_field: bool = True
    omit_non_positional_or_facet_over_positional_channels: bool = True
    omit_table_with_occlusion_if_auto_add_count: bool = True
    omit_vertical_dot_plot: bool = False
    omit_invalid_stack_spec: bool = True
    omit_non_sum_stack: bool = True

    preferred_bin_axis: str = "x"
    preferred_temporal_axis: str = "x"
    preferred_ordinal_axis: str = "y"
    preferred_nominal_axis: str = "y"
    preferred_facet: str = "row"

    # Field encoding constraints
    min_cardinality_for_bin: int = 15
    max_cardinality_for_categorical_color: int = 20
    max_cardinality_for_facet: int = 20
    max_cardinality_for_shape: int = 6
    time_unit_should_have_variation: bool = True
    type_matches_schema_type: bool = True

    # Stylize
    stylize: bool = True
    small_range_step_for_high_cardinality_or_facet: Optional[dict] = None
    nominal_color_scale_for_high_cardinality: Optional[dict] = None
    x_axis_on_top_for_high_y_cardinality_without_column: Optional[dict] = None

    # Effectiveness preference
    max_good_cardinality_for_color: int = 7
    max_good_cardinality_for_facet: int = 5

    # High cardinality strings
    min_percent_unique_for_key: float = 0.8
    min_cardinality_for_key: int = 50

    def __post_init__(self) -> None:
        if self.default_spec_config is None:
            self.default_spec_config = {
                "line": {"point": True},
                "scale": {"useUnaggregatedDomain": True},
            }
        if self.property_precedence is None:
            self.property_precedence = [to_key(p) for p in DEFAULT_PROP_PRECEDENCE]
        if self.enum is None:
            self.enum = dict(DEFAULT_ENUM_INDEX)
        if self.small_range_step_for_high_cardinality_or_facet is None:
            self.small_range_step_for_high_cardinality_or_facet = {
                "maxCardinality": 10,
                "rangeStep": 12,
            }
        if self.nominal_color_scale_for_high_cardinality is None:
            self.nominal_color_scale_for_high_cardinality = {
                "maxCardinality": 10,
                "palette": "category20",
            }
        if self.x_axis_on_top_for_high_y_cardinality_without_column is None:
            self.x_axis_on_top_for_high_y_cardinality_without_column = {
                "maxCardinality": 30,
            }


DEFAULT_QUERY_CONFIG: QueryConfig = QueryConfig()


def extend_config(opt: Optional[QueryConfig] = None, **overrides: Any) -> QueryConfig:
    """Merge overrides into a new QueryConfig, with enum sub-dicts deep-merged."""
    if opt is None:
        opt = QueryConfig()
    base = DEFAULT_QUERY_CONFIG
    merged: dict[str, Any] = {}
    for f in base.__dataclass_fields__:  # type: ignore[attr-defined]
        merged[f] = getattr(opt, f) if hasattr(opt, f) else getattr(base, f)
    merged.update(overrides)
    # Deep-merge enum sub-dicts
    enum = dict(DEFAULT_ENUM_INDEX)
    if merged.get("enum"):
        user_enum: dict = merged["enum"]
        for k, v in user_enum.items():
            if k.endswith("Props") and isinstance(v, dict):
                enum[k] = {**enum.get(k, {}), **v}
            else:
                enum[k] = v
    merged["enum"] = enum
    return QueryConfig(**merged)
