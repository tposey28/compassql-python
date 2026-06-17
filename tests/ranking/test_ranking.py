"""Port of test/ranking/ranking.test.ts"""
from __future__ import annotations

from functools import cmp_to_key

import pytest
from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.model import SpecQueryModel
from compassql.ranking.ranking import comparator_factory, rank
from tests.fixture import schema


def _build(mark, encodings):
    return SpecQueryModel.build(
        {"mark": mark, "encodings": encodings},
        schema,
        DEFAULT_QUERY_CONFIG,
    )


class TestRank:
    def test_empty_group_returns_empty(self):
        group = rank(
            type("G", (), {"items": []})(),
            type("Q", (), {
                "nest": None, "orderBy": None, "chooseBy": "effectiveness",
                "config": DEFAULT_QUERY_CONFIG,
            })(),
            schema,
            0,
        )
        assert group.items == []

    def test_rank_with_dict_group(self):
        group = {"items": []}
        result = rank(
            group,
            {"spec": {"mark": "bar", "encodings": []}, "chooseBy": "effectiveness"},
            schema,
            0,
        )
        assert result["items"] == []


class TestComparatorFactory:
    def test_nested_ranking_uses_second_ranker_on_tie(self):
        # aggregationQuality is the same for both (both aggregate with measure)
        # effectiveness distinguishes them (line > point for temporal x Q)
        specM1 = _build("line", [
            {"channel": "x", "field": "T", "type": "temporal", "timeUnit": "day"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        specM2 = _build("point", [
            {"channel": "x", "field": "T", "type": "temporal", "timeUnit": "day"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        cmp = comparator_factory(["aggregationQuality", "effectiveness"], schema, DEFAULT_QUERY_CONFIG)
        # line should rank better (cmp(m1,m2) < 0 means m1 wins)
        assert cmp(specM1, specM2) < 0

    def test_first_ranker_decides_when_not_tied(self):
        # Raw Q x Q1 has score 1.0 (raw with measure)
        # mean_Q x mean_Q1 has score 0.3 (aggregate without dimension)
        # So specM1 (raw) should beat specM2 (agg)
        specM1 = _build("point", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        specM2 = _build("point", [
            {"aggregate": "mean", "channel": "x", "field": "Q", "type": "quantitative"},
            {"aggregate": "mean", "channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        cmp = comparator_factory(["aggregationQuality", "effectiveness"], schema, DEFAULT_QUERY_CONFIG)
        assert cmp(specM1, specM2) < 0

    def test_single_ranker_returns_zero_on_tie(self):
        # Both are line/point with same agg quality
        specM1 = _build("line", [
            {"channel": "x", "field": "T", "type": "temporal", "timeUnit": "day"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        specM2 = _build("point", [
            {"channel": "x", "field": "T", "type": "temporal", "timeUnit": "day"},
            {"aggregate": "mean", "channel": "y", "field": "Q", "type": "quantitative"},
        ])
        cmp = comparator_factory("aggregationQuality", schema, DEFAULT_QUERY_CONFIG)
        assert cmp(specM1, specM2) == 0

    def test_single_ranker_sorts_by_aggregation_quality(self):
        specM1 = _build("point", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        specM2 = _build("point", [
            {"aggregate": "mean", "channel": "x", "field": "Q", "type": "quantitative"},
            {"aggregate": "mean", "channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        cmp = comparator_factory("aggregationQuality", schema, DEFAULT_QUERY_CONFIG)
        # Raw specM1 (score 1.0) > aggregate specM2 (score 0.3) — specM1 wins
        assert cmp(specM1, specM2) < 0

    def test_sort_list_with_comparator(self):
        specM_raw = _build("point", [
            {"channel": "x", "field": "Q", "type": "quantitative"},
            {"channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        specM_agg = _build("point", [
            {"aggregate": "mean", "channel": "x", "field": "Q", "type": "quantitative"},
            {"aggregate": "mean", "channel": "y", "field": "Q1", "type": "quantitative"},
        ])
        cmp = comparator_factory("aggregationQuality", schema, DEFAULT_QUERY_CONFIG)
        items = [specM_agg, specM_raw]
        items.sort(key=cmp_to_key(cmp))
        # After sorting, raw (higher score) should come first
        assert items[0] is specM_raw
