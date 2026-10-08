"""Tests for compassql.schema.Schema.build_from_data.

Upstream has no equivalent of these: `test/schema.test.ts` builds schemas from
hand-written field lists, so it never exercises the datalib binning arithmetic
against a degenerate column. That arithmetic is where the JS and Python ports
diverge -- JS quietly yields NaN, Python raises -- so the guard needs its own
coverage here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from compassql.schema import ExpandedType, Schema


def bins(schema: Schema, field_name: str) -> dict:
    """`{maxbins: (min, max, distinct, unique)}` for one field, for comparison."""

    fs = schema.field_schema(field_name)
    assert fs is not None, f"no field schema for {field_name!r}"
    return {
        key: (stats.min, stats.max, stats.distinct, stats.unique)
        for key, stats in fs.bin_stats.items()
    }


# Captured from `build_from_data` before the non-finite guard was added, so this
# is a real regression baseline rather than a restatement of current behaviour.
HEALTHY_BINS = {
    "5": (0, 10, 5, {"0": 1, "2": 2, "4": 1, "10": 1}),
    "10": (1.0, 10.0, 9, {"1.0": 1, "2.0": 1, "3.0": 1, "4.0": 1, "10.0": 1}),
    "20": (1.0, 10.0, 18, {"1.0": 1, "2.0": 1, "3.0": 1, "4.0": 1, "10.0": 1}),
}

ZERO_VARIANCE_BINS = {
    "5": (5.0, 5.0, 1, {"5.0": 3}),
    "10": (5.0, 5.0, 1, {"5.0": 3}),
    "20": (5.0, 5.0, 1, {"5.0": 3}),
}


class TestBuildFromDataBinning:
    def test_healthy_column_bin_stats_are_unchanged(self):
        schema = Schema.build_from_data(pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 10.0]}))
        assert bins(schema, "a") == HEALTHY_BINS

    def test_zero_variance_column_still_bins_as_a_single_bucket(self):
        # min == max short-circuits before the binning arithmetic, so the guard
        # must not have moved this onto a different path.
        schema = Schema.build_from_data(pd.DataFrame({"z": [5.0, 5.0, 5.0]}))
        assert bins(schema, "z") == ZERO_VARIANCE_BINS

    def test_all_nan_column_builds_without_raising(self):
        # Real trigger: mds2-3702's `figure_2-conversion` merges two side-by-side
        # tables into one CSV and the second table's temperature column is blank.
        schema = Schema.build_from_data(pd.DataFrame({"b": [np.nan] * 3}))
        fs = schema.field_schema("b")
        assert fs is not None
        # Unbinned, mirroring the JS port's NaN-valued bins: present, unusable.
        assert set(fs.bin_stats) == {"5", "10", "20"}

    def test_empty_column_builds_without_raising(self):
        schema = Schema.build_from_data(pd.DataFrame({"e": pd.Series([], dtype=float)}))
        assert schema.field_schema("e") is not None

    def test_mixed_healthy_and_all_nan_frame_keeps_healthy_bin_stats(self):
        schema = Schema.build_from_data(
            pd.DataFrame(
                {
                    "a": [1.0, 2.0, 3.0, 4.0, 10.0],
                    "b": [np.nan] * 5,
                    "c": [5.0, 5.0, 5.0, 5.0, 5.0],
                }
            )
        )
        assert schema.field_names() == ["a", "b", "c"]
        assert bins(schema, "a") == HEALTHY_BINS
        assert schema.field_schema("b") is not None

    def test_cardinality_of_a_binned_all_nan_field_does_not_raise(self):
        # `cardinality` computes bin stats lazily for maxbins values the build
        # did not precompute, so it reaches `_bin_stats` by a second route.
        schema = Schema.build_from_data(pd.DataFrame({"b": [np.nan] * 3}))
        result = schema.cardinality({"field": "b", "bin": {"maxbins": 7}})
        assert result is not None

    def test_all_nan_column_is_still_typed_quantitative(self):
        schema = Schema.build_from_data(pd.DataFrame({"b": [np.nan] * 3}))
        assert schema.vl_type("b") == ExpandedType.QUANTITATIVE
