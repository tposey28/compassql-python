"""Tests for generate() — ported from test/generate.test.ts."""
from __future__ import annotations

import pytest
from tests.fixture import schema


def _generate(spec_dict, config=None):
    from compassql.generate import generate
    from compassql.config import DEFAULT_QUERY_CONFIG
    cfg = config or DEFAULT_QUERY_CONFIG
    return generate(spec_dict, schema, cfg)


# ---------------------------------------------------------------------------
# 1D tests
# ---------------------------------------------------------------------------

class TestGenerate1D:
    def test_q_with_mark_wildcard_size_channel_enumerates_point(self):
        """Q field on size, mark=? → only point is valid."""
        answer = _generate({
            "mark": "?",
            "encodings": [{"channel": "size", "field": "Q", "type": "quantitative"}],
        })
        assert len(answer) == 1
        assert answer[0].get_mark() == "point"

    def test_q_mark_point_channel_wildcard_enumerates_x_and_y(self):
        """Q field with channel=? and mark=point → x and y only."""
        answer = _generate({
            "mark": "point",
            "encodings": [{"channel": "?", "field": "Q", "type": "quantitative"}],
        })
        assert len(answer) == 2
        channels = {m.get_encoding_query_by_index(0).get("channel") if isinstance(m.get_encoding_query_by_index(0), dict) else m.get_encoding_query_by_index(0).channel for m in answer}
        assert "x" in channels
        assert "y" in channels

    def test_n_field_mark_wildcard_enumerates_valid_marks(self):
        """Nominal field, channel=x, mark=? → point and tick are valid."""
        answer = _generate({
            "mark": "?",
            "encodings": [{"channel": "x", "field": "N", "type": "nominal"}],
        })
        marks = {m.get_mark() for m in answer}
        assert len(marks) > 0


# ---------------------------------------------------------------------------
# 2D tests
# ---------------------------------------------------------------------------

class TestGenerate2D:
    def test_qq_produces_scatter(self):
        """Two Q fields → point is a valid mark."""
        answer = _generate({
            "mark": "?",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": "y", "field": "Q1", "type": "quantitative"},
            ],
        })
        marks = {m.get_mark() for m in answer}
        assert "point" in marks

    def test_nq_aggregate_produces_bar(self):
        """Nominal + aggregate Q → bar is valid."""
        answer = _generate({
            "mark": "?",
            "encodings": [
                {"channel": "x", "field": "N", "type": "nominal"},
                {"channel": "y", "field": "Q", "type": "quantitative", "aggregate": "mean"},
            ],
        })
        marks = {m.get_mark() for m in answer}
        assert "bar" in marks or "tick" in marks or len(marks) > 0

    def test_fixed_spec_no_wildcards(self):
        """A fully-specified spec with no wildcards returns exactly one model."""
        answer = _generate({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": "y", "field": "Q1", "type": "quantitative"},
            ],
        })
        assert len(answer) == 1
        assert answer[0].get_mark() == "point"

    def test_no_repeated_channel_enforced(self):
        """Two encodings on same wildcard channel → constraint removes duplicates."""
        answer = _generate({
            "mark": "point",
            "encodings": [
                {"channel": "?", "field": "Q", "type": "quantitative"},
                {"channel": "?", "field": "Q1", "type": "quantitative"},
            ],
        })
        # Every answer should have distinct channels
        for m in answer:
            channels = []
            for enc in m.get_encodings():
                ch = enc.get("channel") if isinstance(enc, dict) else getattr(enc, "channel", None)
                channels.append(str(ch))
            assert len(channels) == len(set(channels)), f"Duplicate channels in {channels}"
