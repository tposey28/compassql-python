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

CONSTRAINT_MANUALLY_SPECIFIED_CONFIG = DEFAULT_QUERY_CONFIG.__class__(
    **{
        **{f: getattr(DEFAULT_QUERY_CONFIG, f) for f in DEFAULT_QUERY_CONFIG.__dataclass_fields__},
        "constraint_manually_specified_value": True,
    }
)


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
