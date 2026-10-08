"""Port of test/constraint/spec.test.ts (key coverage)"""
from __future__ import annotations

import copy

import pytest

from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.constraint.spec import (
    SPEC_CONSTRAINTS,
    SPEC_CONSTRAINT_INDEX,
    SpecConstraintModel,
)
from compassql.constraint.base import AbstractConstraint
from compassql.model import SpecQueryModel
from compassql.property import Property, get_encoding_nested_prop
from compassql.schema import Schema
from compassql.wildcard import SHORT_WILDCARD

schema = Schema([])

def _config(**overrides):
    """The default QueryConfig with some fields overridden."""

    fields = {f: getattr(DEFAULT_QUERY_CONFIG, f) for f in DEFAULT_QUERY_CONFIG.__dataclass_fields__}
    return DEFAULT_QUERY_CONFIG.__class__(**{**fields, **overrides})


CONSTRAINT_MANUALLY_SPECIFIED_CONFIG = _config(constraint_manually_specified_value=True)


def build_spec_query_model(spec_q: dict) -> SpecQueryModel:
    return SpecQueryModel.build(spec_q, schema, DEFAULT_QUERY_CONFIG)


class TestNonStrictConstraintsHaveConfig:
    def test_non_strict_constraints_have_default_config(self):
        import re
        for constraint in SPEC_CONSTRAINTS:
            if not constraint.strict():
                name = constraint.name()
                snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
                assert hasattr(DEFAULT_QUERY_CONFIG, snake), (
                    f"{name} should have default config but {snake} not found on QueryConfig"
                )


class TestAlwaysIncludeZeroInScaleWithBarMark:
    def test_false_if_scale_does_not_start_at_zero_for_bar(self):
        spec_m = build_spec_query_model({
            "mark": "bar",
            "encodings": [{"channel": "x", "field": "A", "scale": {"zero": False}, "type": "quantitative"}],
        })
        assert not SPEC_CONSTRAINT_INDEX["alwaysIncludeZeroInScaleWithBarMark"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )

    def test_true_if_scale_starts_at_zero_for_bar(self):
        spec_m = build_spec_query_model({
            "mark": "bar",
            "encodings": [{"channel": "x", "field": "A", "scale": {"zero": True}, "type": "quantitative"}],
        })
        assert SPEC_CONSTRAINT_INDEX["alwaysIncludeZeroInScaleWithBarMark"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )


class TestHasAllRequiredPropertiesSpecificSpec:
    spec_c_model = SpecConstraintModel(
        AbstractConstraint(
            name_="TestSpec",
            description="test",
            properties=[
                Property.AGGREGATE,
                Property.TYPE,
                Property.SCALE,
                get_encoding_nested_prop("scale", "type"),
                Property.MARK,
            ],
            allow_wildcard_for_properties=False,
            strict_=True,
        ),
        checker=lambda *args: True,
    )

    def test_true_if_all_properties_defined(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"aggregate": "mean", "channel": "x", "field": "A", "scale": {"type": "log"}, "type": "quantitative"}
            ],
        })
        assert self.spec_c_model.has_all_required_properties_specific(spec_m)

    def test_true_if_required_property_undefined(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [{"aggregate": "mean", "channel": "x", "field": "A", "type": "quantitative"}],
        })
        assert self.spec_c_model.has_all_required_properties_specific(spec_m)

    def test_false_if_required_property_is_wildcard(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"aggregate": "mean", "channel": "x", "field": "A", "scale": SHORT_WILDCARD, "type": "quantitative"}
            ],
        })
        assert not self.spec_c_model.has_all_required_properties_specific(spec_m)

    def test_false_if_nested_required_property_is_wildcard(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"aggregate": "mean", "channel": "x", "field": "A", "scale": {"type": SHORT_WILDCARD}, "type": "quantitative"}
            ],
        })
        assert not self.spec_c_model.has_all_required_properties_specific(spec_m)


class TestNoRepeatedChannel:
    def test_true_when_no_repeated_channels(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative"},
                {"channel": "y", "field": "B", "type": "quantitative"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["noRepeatedChannel"].satisfy(spec_m, schema, DEFAULT_QUERY_CONFIG)

    def test_false_when_repeated_channels(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative"},
                {"channel": "x", "field": "B", "type": "quantitative"},
            ],
        })
        assert not SPEC_CONSTRAINT_INDEX["noRepeatedChannel"].satisfy(spec_m, schema, DEFAULT_QUERY_CONFIG)


class TestHasAllRequiredChannelsForMark:
    def test_true_for_area_line_with_x_and_y(self):
        for mark in ("area", "line"):
            spec_m = build_spec_query_model({
                "mark": mark,
                "encodings": [
                    {"channel": "x", "field": "A", "type": "quantitative"},
                    {"channel": "y", "field": "B", "type": "quantitative"},
                ],
            })
            assert SPEC_CONSTRAINT_INDEX["hasAllRequiredChannelsForMark"].satisfy(
                spec_m, schema, DEFAULT_QUERY_CONFIG
            )

    def test_false_for_area_line_without_x_or_y(self):
        for mark in ("area", "line"):
            spec_m = build_spec_query_model({
                "mark": mark,
                "encodings": [{"channel": "color", "field": "A", "type": "nominal"}],
            })
            assert not SPEC_CONSTRAINT_INDEX["hasAllRequiredChannelsForMark"].satisfy(
                spec_m, schema, DEFAULT_QUERY_CONFIG
            )

    def test_true_for_bar_point_with_x_or_y(self):
        for mark in ("bar", "point"):
            spec_m = build_spec_query_model({
                "mark": mark,
                "encodings": [{"channel": "x", "field": "A", "type": "quantitative"}],
            })
            assert SPEC_CONSTRAINT_INDEX["hasAllRequiredChannelsForMark"].satisfy(
                spec_m, schema, DEFAULT_QUERY_CONFIG
            )

    def test_false_for_text_without_text_channel(self):
        spec_m = build_spec_query_model({
            "mark": "text",
            "encodings": [{"channel": "x", "field": "A", "type": "quantitative"}],
        })
        assert not SPEC_CONSTRAINT_INDEX["hasAllRequiredChannelsForMark"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )

    def test_true_for_text_with_text_channel(self):
        spec_m = build_spec_query_model({
            "mark": "text",
            "encodings": [{"channel": "text", "field": "A", "type": "nominal"}],
        })
        assert SPEC_CONSTRAINT_INDEX["hasAllRequiredChannelsForMark"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )


class TestOmitAggregate:
    def test_true_if_only_raw_data(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative"},
                {"channel": "y", "field": "B", "type": "quantitative"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["omitAggregate"].satisfy(spec_m, schema, DEFAULT_QUERY_CONFIG)

    def test_false_if_aggregate_data(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative", "aggregate": "mean"},
                {"channel": "y", "field": "B", "type": "quantitative"},
            ],
        })
        assert not SPEC_CONSTRAINT_INDEX["omitAggregate"].satisfy(spec_m, schema, DEFAULT_QUERY_CONFIG)


class TestOmitAggregatePlotWithoutDimension:
    def test_false_if_aggregate_and_no_dimension(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative", "aggregate": "mean"},
                {"channel": "y", "field": "B", "type": "quantitative", "aggregate": "mean"},
            ],
        })
        assert not SPEC_CONSTRAINT_INDEX["omitAggregatePlotWithoutDimension"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )

    def test_true_if_aggregate_has_dimension(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "nominal"},
                {"channel": "y", "field": "B", "type": "quantitative", "aggregate": "mean"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["omitAggregatePlotWithoutDimension"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )

    def test_true_if_not_aggregate(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative"},
                {"channel": "y", "field": "B", "type": "quantitative"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["omitAggregatePlotWithoutDimension"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )


class TestOmitRepeatedField:
    def test_true_for_non_repeated_fields(self):
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative"},
                {"channel": "y", "field": "B", "type": "quantitative"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["omitRepeatedField"].satisfy(spec_m, schema, DEFAULT_QUERY_CONFIG)

    def test_true_for_repeated_fields_not_enumerated(self):
        # TS: "should return true when repeated fields are not enumerated"
        # Without constraintManuallySpecifiedValue or field wildcards, repeated fields are allowed
        spec_m = build_spec_query_model({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative"},
                {"channel": "y", "field": "A", "type": "quantitative"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["omitRepeatedField"].satisfy(spec_m, schema, DEFAULT_QUERY_CONFIG)


class TestOmitBarLineAreaWithOcclusion:
    def test_false_for_raw_bar_line_area(self):
        for mark in ("bar", "line", "area"):
            spec_m = build_spec_query_model({
                "mark": mark,
                "encodings": [
                    {"channel": "x", "field": "A", "type": "quantitative"},
                    {"channel": "y", "field": "B", "type": "quantitative"},
                ],
            })
            assert not SPEC_CONSTRAINT_INDEX["omitBarLineAreaWithOcclusion"].satisfy(
                spec_m, schema, DEFAULT_QUERY_CONFIG
            )

    def test_true_for_aggregate_bar(self):
        spec_m = build_spec_query_model({
            "mark": "bar",
            "encodings": [
                {"channel": "x", "field": "A", "type": "nominal"},
                {"channel": "y", "field": "B", "type": "quantitative", "aggregate": "mean"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["omitBarLineAreaWithOcclusion"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )


# Ten rows, one column per case the measured mode has to distinguish:
# a quantitative x with one row per value, the same shape with each value
# repeated, and a nominal x whose categories are all distinct.
MEASURED_ROWS = [
    {
        "unique_q": float(i),
        "repeat_q": float(i // 2),
        "unique_n": chr(ord("a") + i),
        "dep": float(i) * 2.0,
    }
    for i in range(10)
]
measured_schema = Schema.build_from_data(MEASURED_ROWS)

MEASURING_CONFIG = _config(measure_occlusion=True)


def _occlusion_spec(mark: str, x_field: str, x_type: str, aggregate: str | None = None) -> dict:
    y_enc = {"channel": "y", "field": "dep", "type": "quantitative"}
    if aggregate:
        y_enc["aggregate"] = aggregate
    return {
        "mark": mark,
        "encodings": [{"channel": "x", "field": x_field, "type": x_type}, y_enc],
    }


def _admits(spec_q: dict, opt) -> bool:
    spec_m = SpecQueryModel.build(spec_q, measured_schema, opt)
    return SPEC_CONSTRAINT_INDEX["omitBarLineAreaWithOcclusion"].satisfy(
        spec_m, measured_schema, opt
    )


class TestOmitBarLineAreaWithMeasuredOcclusion:
    """`measure_occlusion` makes the constraint consult the data.

    Off (the default) it must behave exactly as upstream does, whatever the
    schema says; on, a raw plot survives only when its x values do not repeat.
    """

    @pytest.mark.parametrize("mark", ["bar", "line", "area"])
    def test_default_still_prunes_a_raw_plot_over_a_unique_x(self, mark):
        """The schema now says this plot does not occlude. The default must not
        care -- that is the upstream behaviour the flag exists to opt out of."""
        assert not _admits(
            _occlusion_spec(mark, "unique_q", "quantitative"), DEFAULT_QUERY_CONFIG
        )

    @pytest.mark.parametrize("mark", ["bar", "line", "area"])
    def test_default_still_admits_an_aggregate_plot(self, mark):
        assert _admits(
            _occlusion_spec(mark, "unique_n", "nominal", aggregate="mean"),
            DEFAULT_QUERY_CONFIG,
        )

    @pytest.mark.parametrize("mark", ["bar", "line", "area"])
    def test_measured_admits_a_continuous_x_with_one_row_per_value(self, mark):
        """Nothing overlaps, so none of the three marks occludes."""
        assert _admits(_occlusion_spec(mark, "unique_q", "quantitative"), MEASURING_CONFIG)

    @pytest.mark.parametrize("mark", ["bar", "line", "area"])
    def test_measured_prunes_a_repeating_x(self, mark):
        """Two rows per x value: the marks land on top of each other."""
        assert not _admits(_occlusion_spec(mark, "repeat_q", "quantitative"), MEASURING_CONFIG)

    def test_measured_admits_a_bar_over_distinct_categories(self):
        """One bar per category is the ordinary bar chart, not an occluded one."""
        assert _admits(_occlusion_spec("bar", "unique_n", "nominal"), MEASURING_CONFIG)

    @pytest.mark.parametrize("mark", ["line", "area"])
    def test_measured_prunes_line_and_area_over_categories(self, mark):
        """They interpolate between points, and there is nothing between two
        unrelated categories to interpolate over -- `line|x:treatment,n` draws a
        trend across treatment groups that does not exist."""
        assert not _admits(_occlusion_spec(mark, "unique_n", "nominal"), MEASURING_CONFIG)

    @pytest.mark.parametrize("mark", ["bar", "line", "area"])
    def test_measured_prunes_when_there_is_no_x_encoding(self, mark):
        """Nothing to measure, so stay with upstream's answer."""
        spec_q = {
            "mark": mark,
            "encodings": [{"channel": "y", "field": "dep", "type": "quantitative"}],
        }
        assert not _admits(spec_q, MEASURING_CONFIG)

    @pytest.mark.parametrize("mark", ["bar", "line", "area"])
    def test_measured_prunes_a_field_the_schema_does_not_carry(self, mark):
        """Also must not raise: the schema a query is run against need not be
        the one its fields were named from."""
        assert not _admits(
            _occlusion_spec(mark, "not_in_the_schema", "quantitative"), MEASURING_CONFIG
        )

    def test_measured_admits_a_temporal_x(self):
        """Temporal counts as continuous -- a measured time series is the case
        the whole option exists for."""
        rows = [{"t": f"2024-01-{day:02d}", "dep": float(day)} for day in range(1, 13)]
        temporal_schema = Schema.build_from_data(rows)
        spec_q = {
            "mark": "line",
            "encodings": [
                {"channel": "x", "field": "t", "type": "temporal"},
                {"channel": "y", "field": "dep", "type": "quantitative"},
            ],
        }
        spec_m = SpecQueryModel.build(spec_q, temporal_schema, MEASURING_CONFIG)
        assert SPEC_CONSTRAINT_INDEX["omitBarLineAreaWithOcclusion"].satisfy(
            spec_m, temporal_schema, MEASURING_CONFIG
        )


class TestHasAppropriateGraphicTypeForMark:
    def test_true_for_bar_with_dimension_and_measure(self):
        spec_m = build_spec_query_model({
            "mark": "bar",
            "encodings": [
                {"channel": "x", "field": "A", "type": "nominal"},
                {"channel": "y", "field": "B", "type": "quantitative", "aggregate": "mean"},
            ],
        })
        assert SPEC_CONSTRAINT_INDEX["hasAppropriateGraphicTypeForMark"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )

    def test_false_for_bar_with_two_dimensions(self):
        spec_m = build_spec_query_model({
            "mark": "bar",
            "encodings": [
                {"channel": "x", "field": "A", "type": "nominal"},
                {"channel": "y", "field": "B", "type": "nominal"},
            ],
        })
        assert not SPEC_CONSTRAINT_INDEX["hasAppropriateGraphicTypeForMark"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )

    def test_false_for_bar_with_two_measures(self):
        spec_m = build_spec_query_model({
            "mark": "bar",
            "encodings": [
                {"channel": "x", "field": "A", "type": "quantitative", "aggregate": "mean"},
                {"channel": "y", "field": "B", "type": "quantitative", "aggregate": "mean"},
            ],
        })
        assert not SPEC_CONSTRAINT_INDEX["hasAppropriateGraphicTypeForMark"].satisfy(
            spec_m, schema, DEFAULT_QUERY_CONFIG
        )
