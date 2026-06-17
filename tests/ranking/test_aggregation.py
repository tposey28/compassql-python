"""Port of test/ranking/aggregation.test.ts"""
from __future__ import annotations

import pytest
from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.model import SpecQueryModel
from compassql.ranking.aggregation import score
from compassql.wildcard import SHORT_WILDCARD
from tests.fixture import schema


AGGREGATE_OPS = {"mean", "sum", "count", "min", "max", "average", "median", "q1", "q3"}
TIME_UNITS = {"year", "month", "day", "date", "hours", "minutes", "seconds", "quarter"}


def _build_spec_model(field_str: str) -> SpecQueryModel:
    """Build a SpecQueryModel from a shorthand string like 'mean_Q x bin_Q1 x count_*'."""
    encodings = []
    for part in field_str.split("x"):
        part = part.strip()
        enc_q = {"channel": SHORT_WILDCARD}
        tokens = part.split("_")

        if len(tokens) > 1:
            fn = tokens[0]
            field = "_".join(tokens[1:])
        else:
            fn = None
            field = tokens[0]

        enc_q["field"] = field
        # Determine type from schema
        fs = schema.field_schema(field)
        if fs is not None:
            enc_q["type"] = fs.vl_type.value
        elif field == "*":
            enc_q["type"] = "quantitative"
        else:
            enc_q["type"] = "quantitative"

        if fn == "bin":
            enc_q["bin"] = True
        elif fn in TIME_UNITS:
            enc_q["timeUnit"] = fn
        elif fn in AGGREGATE_OPS:
            enc_q["aggregate"] = fn

        encodings.append(enc_q)

    return SpecQueryModel.build(
        {"mark": SHORT_WILDCARD, "encodings": encodings},
        schema,
        DEFAULT_QUERY_CONFIG,
    )


def _get_score(field_str: str) -> float:
    return score(_build_spec_model(field_str), schema, DEFAULT_QUERY_CONFIG)["score"]


class TestAggregationQuality:
    def test_raw_with_measure_beats_raw_without(self):
        # Raw with Q measure should score higher than raw nominal only
        assert _get_score("Q") > _get_score("N")

    def test_aggregate_with_dimension_beats_no_dimension(self):
        # N x mean_Q has a dimension (N) so scores 0.9; mean_Q alone has no dimension (0.3)
        assert _get_score("N x mean_Q") > _get_score("mean_Q")

    def test_raw_measure_beats_aggregate_with_count(self):
        # Raw with Q measure (score 1.0) beats aggregate with count (0.8)
        assert _get_score("Q") > _get_score("N x count_*")

    def test_aggregate_without_count_and_bin_beats_with_bin(self):
        # mean_Q (0.9) > bin_Q x count_* (0.8) > bin_Q x mean_Q1 (0.7ish)
        assert _get_score("N x mean_Q") > _get_score("N x bin_Q x count_*")

    def test_aggregate_with_raw_continuous_penalized(self):
        # Aggregate with raw continuous field as dimension is penalized (0.1)
        # Q x mean_Q1 — Q is raw continuous in an aggregate context
        s = _get_score("Q x mean_Q")
        assert s == pytest.approx(0.1)

    def test_aggregate_without_dimension_penalized(self):
        # mean_Q x mean_Q1 — no dimensions
        s = _get_score("mean_Q x mean_Q")
        assert s == pytest.approx(0.3)

    def test_raw_without_measure_penalized(self):
        # N x O — no measures
        s = _get_score("N x O")
        assert s == pytest.approx(0.2)

    def test_1d_ordering(self):
        # Q, T > bin_Q x count_* > mean_Q > O, N
        raw_q = _get_score("Q")
        raw_t = _get_score("T")
        bin_count = _get_score("bin_Q x count_*")
        mean_q = _get_score("mean_Q")
        ordinal = _get_score("O")
        nominal = _get_score("N")

        assert raw_q == raw_t  # both raw with measure
        assert raw_q > bin_count
        assert bin_count > mean_q  # 0.8 vs ... wait, mean_Q has no dimension
        # Actually mean_Q has no dimension -> score 0.3, bin_count is 0.8
        assert _get_score("N x bin_Q x count_*") > mean_q
        assert ordinal == nominal  # both raw without measure

    def test_scores_match_expected_values(self):
        assert _get_score("Q") == pytest.approx(1.0)
        assert _get_score("N") == pytest.approx(0.2)
        assert _get_score("N x mean_Q") == pytest.approx(0.9)
        assert _get_score("N x count_*") == pytest.approx(0.8)
        assert _get_score("N x bin_Q x count_*") == pytest.approx(0.8)
        assert _get_score("mean_Q") == pytest.approx(0.3)
        assert _get_score("Q x mean_Q") == pytest.approx(0.1)
