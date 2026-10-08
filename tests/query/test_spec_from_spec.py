"""Tests for from_spec / Query.from_dict encoding forms.

A CompassQL *query* puts encodings in a list so that `channel` can itself be a
wildcard; Vega-Lite keys them by channel, which cannot express `{"channel": "?"}`
because a dict cannot be keyed by "?". from_spec accepts both.
"""
from __future__ import annotations

import pytest

from compassql.query.query import Query
from compassql.query.spec import from_spec
from compassql.wildcard import is_wildcard


def _channels(spec_q):
    out = []
    for enc in spec_q.encodings:
        out.append(enc.get("channel") if isinstance(enc, dict) else getattr(enc, "channel", None))
    return out


def _fields(spec_q):
    out = []
    for enc in spec_q.encodings:
        out.append(enc.get("field") if isinstance(enc, dict) else getattr(enc, "field", None))
    return out


class TestEncodingsListForm:
    def test_reads_encodings_list(self):
        spec_q = from_spec({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": "y", "field": "Q1", "type": "quantitative"},
            ],
        })
        assert len(spec_q.encodings) == 2
        assert _channels(spec_q) == ["x", "y"]
        assert _fields(spec_q) == ["Q", "Q1"]

    def test_preserves_a_short_channel_wildcard(self):
        """The whole reason the list form exists."""
        spec_q = from_spec({
            "mark": "?",
            "encodings": [{"channel": "?", "field": "Q", "type": "quantitative"}],
        })
        assert is_wildcard(_channels(spec_q)[0])

    def test_preserves_an_enum_wildcard(self):
        spec_q = from_spec({
            "mark": "point",
            "encodings": [{"channel": {"enum": ["x", "y"]}, "field": "Q", "type": "quantitative"}],
        })
        channel = _channels(spec_q)[0]
        assert is_wildcard(channel)
        assert channel["enum"] == ["x", "y"]

    def test_two_encodings_can_share_a_wildcard_channel(self):
        """Impossible in the Vega-Lite dict form -- both would collide on "?"."""
        spec_q = from_spec({
            "mark": "?",
            "encodings": [
                {"channel": "?", "field": "Q", "type": "quantitative"},
                {"channel": "?", "field": "Q1", "type": "quantitative"},
            ],
        })
        assert len(spec_q.encodings) == 2
        assert _fields(spec_q) == ["Q", "Q1"]

    def test_autocount_shorthand_still_applies(self):
        spec_q = from_spec({
            "mark": "bar",
            "encodings": [{"channel": "y", "aggregate": "count", "type": "quantitative"}],
        })
        assert _fields(spec_q) == ["*"]

    def test_empty_list_is_allowed(self):
        assert from_spec({"mark": "point", "encodings": []}).encodings == []


class TestVegaLiteDictFormUnchanged:
    def test_reads_encoding_dict(self):
        spec_q = from_spec({
            "mark": "point",
            "encoding": {
                "x": {"field": "Q", "type": "quantitative"},
                "y": {"field": "Q1", "type": "quantitative"},
            },
        })
        assert sorted(_channels(spec_q)) == ["x", "y"]
        assert sorted(_fields(spec_q)) == ["Q", "Q1"]

    def test_autocount_shorthand_still_applies(self):
        spec_q = from_spec({
            "mark": "bar",
            "encoding": {"y": {"aggregate": "count", "type": "quantitative"}},
        })
        assert _fields(spec_q) == ["*"]

    def test_missing_encoding_yields_no_encodings(self):
        assert from_spec({"mark": "point"}).encodings == []


class TestConflictingForms:
    def test_both_forms_is_an_error(self):
        with pytest.raises(ValueError, match="exactly one"):
            from_spec({
                "mark": "point",
                "encodings": [{"channel": "x", "field": "Q", "type": "quantitative"}],
                "encoding": {"y": {"field": "Q1", "type": "quantitative"}},
            })

    def test_non_list_encodings_is_an_error(self):
        with pytest.raises(ValueError, match="must be a list"):
            from_spec({"mark": "point", "encodings": {"x": {"field": "Q"}}})


class TestThroughQueryFromDict:
    def test_query_from_dict_carries_the_list_form(self):
        """The end goal: a wildcard query expressible as a plain dict."""
        query = Query.from_dict({
            "spec": {
                "mark": "?",
                "encodings": [
                    {"channel": "?", "field": "Q", "type": "quantitative"},
                    {"channel": "?", "field": "Q1", "type": "quantitative"},
                ],
            },
            "orderBy": "effectiveness",
        })
        assert len(query.spec.encodings) == 2
        assert all(is_wildcard(c) for c in _channels(query.spec))
        assert query.orderBy == "effectiveness"

    def test_end_to_end_recommend_from_a_plain_dict(self):
        """Previously impossible: Query.from_dict produced an empty encoding set
        for a wildcard-channel query, so recommend() returned a bare spec."""
        import pandas as pd

        from compassql import Schema, recommend
        from compassql.result import iter_leaves

        df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2.0, 4.0, 6.0, 8.0]})
        query = Query.from_dict({
            "spec": {
                "mark": "?",
                "encodings": [
                    {"channel": "?", "field": "a", "type": "quantitative"},
                    {"channel": "?", "field": "b", "type": "quantitative"},
                ],
                "data": {"values": []},
            },
            "orderBy": "effectiveness",
            "config": {"autoAddCount": False},
        })
        leaves = list(iter_leaves(recommend(query, Schema.build_from_data(df))["result"]))
        assert leaves
        assert leaves[0].to_shorthand() == "point|x:a,q|y:b,q"
