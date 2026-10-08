"""Port of test/ranking/effectiveness/*.test.ts"""
from __future__ import annotations

import pytest
from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.model import SpecQueryModel
from compassql.ranking.effectiveness import effectiveness
from compassql.ranking.effectiveness.mark import MarkScorer, featurize
from compassql.ranking.effectiveness.typechannel import TypeChannelScorer, TERRIBLE
from compassql.ranking.effectiveness.type import Q, BIN_Q, TIMEUNIT_T, N, K, T
from tests.fixture import schema


def _build(mark, encodings):
    return SpecQueryModel.build(
        {"mark": mark, "encodings": encodings},
        schema,
        DEFAULT_QUERY_CONFIG,
    )


def _eff_score(mark, encodings) -> float:
    m = _build(mark, encodings)
    return effectiveness(m, schema, DEFAULT_QUERY_CONFIG)["score"]


class TestMarkScorer:
    def setup_method(self):
        self.scorer = MarkScorer()

    def test_point_beats_bar_for_qq(self):
        # QxQ with occlusion: point=0, bar=-2
        assert self.scorer.score_index[featurize(Q, Q, True, "point")] == 0
        assert self.scorer.score_index[featurize(Q, Q, True, "bar")] == -2

    def test_line_beats_point_for_temporal_q(self):
        # For no-occlusion temporal x Q: line=0, point=-0.3
        assert self.scorer.score_index[featurize(T, TIMEUNIT_T, False, "line")] == 0
        assert self.scorer.score_index[featurize(T, TIMEUNIT_T, False, "point")] == -0.3

    def test_bar_best_for_q_x_nominal(self):
        # No occlusion Q x N: bar=0
        assert self.scorer.score_index[featurize(Q, N, False, "bar")] == 0

    def test_rule_worst(self):
        # rule is always -2.5
        assert self.scorer.score_index[featurize(Q, Q, True, "rule")] == -2.5
        assert self.scorer.score_index[featurize(N, N, False, "rule")] == -2.5

    def test_circle_treated_as_point(self):
        m = _build("circle", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        scores = self.scorer.get_score(m, schema, DEFAULT_QUERY_CONFIG)
        # Should return same score as point for QxQ
        point_score = self.scorer.score_index[featurize(Q, Q, True, "point")]
        assert scores[0]["score"] == point_score

    def test_dd_point_and_rect_equal(self):
        # DxD: point=0, rect=0
        assert self.scorer.score_index[featurize(N, N, True, "point")] == 0
        assert self.scorer.score_index[featurize(N, N, True, "rect")] == 0


class TestTypeChannelScorer:
    def setup_method(self):
        self.scorer = TypeChannelScorer()

    def test_q_on_x_y_best(self):
        assert self.scorer.score_index[self.scorer.featurize(Q, "x")] == 0
        assert self.scorer.score_index[self.scorer.featurize(Q, "y")] == 0

    def test_q_on_shape_terrible(self):
        assert self.scorer.score_index[self.scorer.featurize(Q, "shape")] == TERRIBLE

    def test_n_on_xy_good(self):
        assert self.scorer.score_index[self.scorer.featurize(N, "x")] == 0
        assert self.scorer.score_index[self.scorer.featurize(N, "y")] == 0

    def test_n_on_size_penalized(self):
        assert self.scorer.score_index[self.scorer.featurize(N, "size")] == -3.0

    def test_k_on_position_less_penalized(self):
        # K on x/y is -1, but K on size is nominal_size - 2 = -5
        assert self.scorer.score_index[self.scorer.featurize(K, "x")] == -1.0
        assert self.scorer.score_index[self.scorer.featurize(K, "size")] == -5.0

    def test_bin_q_on_row_col_penalty(self):
        # BIN_Q on row/column: -0.75
        assert self.scorer.score_index[self.scorer.featurize(BIN_Q, "row")] == -0.75
        assert self.scorer.score_index[self.scorer.featurize(BIN_Q, "column")] == -0.75


class TestEffectiveness:
    def test_aggregate_line_beats_point_for_temporal(self):
        line_score = _eff_score("line", [
            {"channel": "x", "field": "T", "type": "temporal", "timeUnit": "year"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        point_score = _eff_score("point", [
            {"channel": "x", "field": "T", "type": "temporal", "timeUnit": "year"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        assert line_score > point_score

    def test_bar_beats_point_for_nominal_x_q(self):
        bar_score = _eff_score("bar", [
            {"channel": "x", "field": "N", "type": "nominal"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        point_score = _eff_score("point", [
            {"channel": "x", "field": "N", "type": "nominal"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        assert bar_score > point_score

    def test_scatter_beats_bar_for_raw_qq(self):
        point_score = _eff_score("point", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        bar_score = _eff_score("bar", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        assert point_score > bar_score

    def test_x_y_channels_better_than_color_for_q(self):
        xy_score = _eff_score("point", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        color_score = _eff_score("point", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "color", "field": "Q1", "type": "quantitative"},
        ])
        assert xy_score > color_score

    def test_effectiveness_returns_dict_with_score_and_features(self):
        m = _build("bar", [
            {"channel": "x", "field": "N", "type": "nominal"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        result = effectiveness(m, schema, DEFAULT_QUERY_CONFIG)
        assert "score" in result
        assert "features" in result
        assert isinstance(result["features"], list)
