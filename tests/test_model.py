"""Unit tests for SpecQueryModel — ported from test/model.test.ts."""
from __future__ import annotations

import sys
_venv = "/home/julsey/.virtualenvs/NIST-Discvr/lib/python3.12/site-packages"
if _venv not in sys.path:
    sys.path.insert(0, _venv)

import pytest
from tests.fixture import schema
from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.model import SpecQueryModel
from compassql.query.spec import SpecQuery
from compassql.query.encoding import FieldQuery
from compassql.wildcard import SHORT_WILDCARD, Wildcard, is_wildcard
from compassql.property import ENCODING_TOPLEVEL_PROPS


def build(spec_q: SpecQuery) -> SpecQueryModel:
    return SpecQueryModel.build(spec_q, schema, DEFAULT_QUERY_CONFIG)


class TestSpecQueryModelBuild:
    def test_mark_wildcard_short(self):
        spec_q = SpecQuery(mark=SHORT_WILDCARD, encodings=[])
        m = build(spec_q)
        assert m.wildcard_index.mark is not None
        assert m.wildcard_index.mark.name == "m"
        assert m.wildcard_index.mark.enum == DEFAULT_QUERY_CONFIG.enum["mark"]

    def test_mark_wildcard_full(self):
        spec_q = SpecQuery(mark=Wildcard(enum=["bar"]), encodings=[])
        m = build(spec_q)
        assert m.wildcard_index.mark is not None
        assert m.wildcard_index.mark.enum == ["bar"]

    def test_mark_specific_no_wildcard_index(self):
        spec_q = SpecQuery(mark="bar", encodings=[])
        m = build(spec_q)
        assert m.wildcard_index.mark is None

    def test_encoding_field_without_type_auto_adds_type_wildcard(self):
        spec_q = SpecQuery(
            mark="point",
            encodings=[FieldQuery(channel="x", field="A")],
        )
        m = build(spec_q)
        enc_q = m.get_encoding_query_by_index(0)
        assert is_wildcard(enc_q.type)
        assert m.wildcard_index.encodings[0].get("type") is not None

    def test_encoding_toplevel_prop_short_wildcard_is_indexed(self):
        for prop in ENCODING_TOPLEVEL_PROPS:
            if prop in ("channel", "field", "type", "value", "autoCount"):
                continue
            spec_q = SpecQuery(
                mark="point",
                encodings=[FieldQuery(channel="x", field="a", type="quantitative", **{prop: SHORT_WILDCARD})],
            )
            m = build(spec_q)
            assert m.wildcard_index.encoding_indices_by_property.get(prop) is not None, \
                f"Expected wildcard index for prop={prop}"
            assert m.wildcard_index.encodings[0].get(prop) is not None, \
                f"Expected encoding wildcard for prop={prop}"

    def test_get_mark(self):
        spec_q = SpecQuery(mark="point", encodings=[])
        m = build(spec_q)
        assert m.get_mark() == "point"

    def test_set_and_reset_mark(self):
        spec_q = SpecQuery(mark=SHORT_WILDCARD, encodings=[])
        m = build(spec_q)
        m.set_mark("bar")
        assert m.get_mark() == "bar"
        m.reset_mark()
        assert is_wildcard(m.get_mark())

    def test_duplicate_is_independent_copy(self):
        spec_q = SpecQuery(mark=SHORT_WILDCARD, encodings=[FieldQuery(channel="x", field="price", type="quantitative")])
        m = build(spec_q)
        copy = m.duplicate()
        copy.set_mark("bar")
        # original should still have wildcard mark, not "bar"
        assert is_wildcard(m.get_mark())

    def test_to_shorthand_returns_string(self):
        spec_q = SpecQuery(
            mark="bar",
            encodings=[FieldQuery(channel="x", field="Q", type="quantitative", aggregate="mean")],
        )
        m = build(spec_q)
        sh = m.to_shorthand()
        assert isinstance(sh, str)
        assert "bar" in sh
        assert "mean" in sh
