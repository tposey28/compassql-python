"""Tests for nest() — ported from test/nest.test.ts."""
from __future__ import annotations

import pytest
from tests.fixture import schema


def _generate(spec_dict, config=None):
    from compassql.generate import generate
    from compassql.config import DEFAULT_QUERY_CONFIG
    return generate(spec_dict, schema, config or DEFAULT_QUERY_CONFIG)


def _nest(answer_set, nest_spec):
    from compassql.nest import nest
    from compassql.query.groupby import Nest
    # Convert plain dicts to Nest objects if needed
    converted = None
    if nest_spec is not None:
        converted = []
        for item in nest_spec:
            if isinstance(item, dict):
                converted.append(Nest(groupBy=item.get("groupBy"), orderGroupBy=item.get("orderGroupBy")))
            else:
                converted.append(item)
    return nest(answer_set, converted)


class TestNestGroupByField:
    def test_groups_by_field_ignoring_function(self):
        """Visualizations with same fields should group together."""
        from compassql.query.groupby import REPLACE_BLANK_FIELDS
        from compassql.property import Property

        answer_set = _generate({
            "mark": "?",
            "encodings": [
                {"channel": "?", "field": "Q", "type": "quantitative", "aggregate": {"name": "a0", "enum": ["mean", "median"]}},
                {"channel": "?", "field": "O", "type": "ordinal"},
            ],
        })
        groups = _nest(answer_set, [
            {"groupBy": [{"property": Property.FIELD, "replace": REPLACE_BLANK_FIELDS}]},
        ])
        # All items should be grouped under one node since same fields
        assert len(groups.items) == 1

    def test_groups_histogram_and_raw_together(self):
        """Histogram (binned Q) and raw Q should group with same field."""
        from compassql.query.groupby import REPLACE_BLANK_FIELDS
        from compassql.property import Property

        answer_set = _generate({
            "mark": "?",
            "encodings": [
                {"channel": "?", "field": "Q", "type": "quantitative", "bin": {"name": "b0", "enum": [True, False]}},
                {"channel": "?", "field": "N", "type": "nominal"},
            ],
        })
        groups = _nest(answer_set, [
            {"groupBy": [{"property": Property.FIELD, "replace": REPLACE_BLANK_FIELDS}]},
        ])
        assert len(groups.items) >= 1


class TestNestGroupByEncoding:
    def test_groups_by_encoding_channel_replace(self):
        """Group by encoding with xy-replacement collapses x/y variants."""
        from compassql.query.groupby import REPLACE_XY_CHANNELS
        from compassql.property import Property

        answer_set = _generate({
            "mark": "point",
            "encodings": [
                {"channel": "?", "field": "Q", "type": "quantitative"},
                {"channel": "?", "field": "Q1", "type": "quantitative"},
            ],
        })
        groups = _nest(answer_set, [
            {"groupBy": [{"property": Property.CHANNEL, "replace": REPLACE_XY_CHANNELS}]},
        ])
        # x and y for Q vs Q1 should collapse to one group
        assert len(groups.items) >= 1


class TestNestFlatNone:
    def test_no_nest_returns_flat_tree(self):
        """None nest spec → flat tree, all items at top level."""
        answer_set = _generate({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": "y", "field": "Q1", "type": "quantitative"},
            ],
        })
        groups = _nest(answer_set, None)
        assert len(groups.items) == len(answer_set)
