"""Unit tests for compassql.query.shorthand — ported from test/query/shorthand.test.ts."""
from __future__ import annotations

import sys
_venv = "/home/julsey/.virtualenvs/NIST-Discvr/lib/python3.12/site-packages"
if _venv not in sys.path:
    sys.path.insert(0, _venv)

import pytest
from compassql.query.shorthand import (
    spec as spec_shorthand,
    encoding as encoding_shorthand,
    field_def as field_def_shorthand,
    get_replacer,
    INCLUDE_ALL,
    REPLACE_NONE,
    parse,
    vlspec,
    _split_with_tail,
)
from compassql.query.spec import SpecQuery
from compassql.query.encoding import FieldQuery, AutoCountQuery, ValueQuery
from compassql.wildcard import SHORT_WILDCARD


class TestVlSpec:
    def test_basic_vl_spec_shorthand(self):
        result = vlspec({
            "mark": "point",
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
            },
        })
        assert "point" in result
        assert "x" in result
        assert "x,q" in result

    def test_vl_spec_with_transform(self):
        result = vlspec({
            "transform": [{"filter": "datum.x === 5"}, {"calculate": "datum.x*2", "as": "x2"}],
            "mark": "point",
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
            },
        })
        assert "transform:" in result
        assert "point" in result
        assert "x,q" in result


class TestSplitWithTail:
    def test_basic_split(self):
        result = _split_with_tail("012-345-678-9", "-", 2)
        assert result == ["012", "345", "678-9"]

    def test_count_greater_than_delimiters(self):
        result = _split_with_tail("012-345", "-", 3)
        assert result == ["012", "345", "", ""]


class TestParse:
    def test_parse_simple(self):
        spec_q = parse("point|x:Q,q|y:N,n")
        assert spec_q.mark == "point"
        assert len(spec_q.encodings) == 2

    def test_parse_with_aggregate(self):
        spec_q = parse("bar|x:mean(Q,q)|y:N,n")
        assert spec_q.mark == "bar"
        enc_x = next(e for e in spec_q.encodings if e.channel == "x")
        assert enc_x.aggregate == "mean"
        assert enc_x.field == "Q"

    def test_parse_with_bin(self):
        spec_q = parse("point|x:bin(balance,q)|y:Q,q")
        enc_x = next(e for e in spec_q.encodings if e.channel == "x")
        assert enc_x.bin == {} or enc_x.bin is not None

    def test_parse_with_transform(self):
        spec_q = parse('point|transform:[{"filter":"datum.x > 5"}]|x:Q,q')
        assert spec_q.transform == [{"filter": "datum.x > 5"}]
        assert len(spec_q.encodings) == 1

    def test_parse_wildcard_mark(self):
        spec_q = parse("?|x:Q,q")
        assert spec_q.mark == SHORT_WILDCARD

    def test_parse_short_wildcard_channel(self):
        spec_q = parse("point|?:Q,q")
        assert spec_q.encodings[0].channel == SHORT_WILDCARD


class TestSpecShorthand:
    def test_mark_only(self):
        spec_q = SpecQuery(mark="bar", encodings=[])
        result = spec_shorthand(spec_q)
        assert result == "bar"

    def test_with_encoding(self):
        spec_q = SpecQuery(
            mark="point",
            encodings=[FieldQuery(channel="x", field="price", type="quantitative")],
        )
        result = spec_shorthand(spec_q)
        assert "point" in result
        assert "x:price,q" in result

    def test_encodings_are_sorted(self):
        spec_q = SpecQuery(
            mark="point",
            encodings=[
                FieldQuery(channel="y", field="y_field", type="quantitative"),
                FieldQuery(channel="x", field="x_field", type="ordinal"),
            ],
        )
        result = spec_shorthand(spec_q)
        parts = result.split("|")
        enc_parts = [p for p in parts if ":" in p]
        assert enc_parts == sorted(enc_parts)

    def test_disabled_autocount_excluded(self):
        from compassql.query.encoding import AutoCountQuery
        spec_q = SpecQuery(
            mark="point",
            encodings=[
                FieldQuery(channel="x", field="Q", type="quantitative"),
                AutoCountQuery(channel="y", autoCount=False),
            ],
        )
        result = spec_shorthand(spec_q)
        assert "autocount" not in result


class TestEncodingShorthand:
    def test_field_query(self):
        enc_q = FieldQuery(channel="x", field="price", type="quantitative")
        result = encoding_shorthand(enc_q)
        assert result == "x:price,q"

    def test_aggregate_field_query(self):
        enc_q = FieldQuery(channel="x", field="price", type="quantitative", aggregate="mean")
        result = encoding_shorthand(enc_q)
        assert result == "x:mean(price,q)"

    def test_autocount_query(self):
        enc_q = AutoCountQuery(channel="y", autoCount=True)
        result = encoding_shorthand(enc_q)
        assert result == "y:autocount()"

    def test_value_query(self):
        enc_q = ValueQuery(channel="color", value="red")
        result = encoding_shorthand(enc_q)
        assert result == "color:red"

    def test_wildcard_channel(self):
        enc_q = FieldQuery(channel=SHORT_WILDCARD, field="price", type="quantitative")
        result = encoding_shorthand(enc_q)
        assert result.startswith("?:")

    def test_bin_field(self):
        enc_q = FieldQuery(channel="x", field="price", type="quantitative", bin=True)
        result = encoding_shorthand(enc_q)
        assert result == "x:bin(price,q)"

    def test_ordinal_type_short(self):
        enc_q = FieldQuery(channel="x", field="cat", type="ordinal")
        result = encoding_shorthand(enc_q)
        assert result == "x:cat,o"

    def test_nominal_type_short(self):
        enc_q = FieldQuery(channel="color", field="species", type="nominal")
        result = encoding_shorthand(enc_q)
        assert result == "color:species,n"

    def test_temporal_type_short(self):
        enc_q = FieldQuery(channel="x", field="date", type="temporal")
        result = encoding_shorthand(enc_q)
        assert result == "x:date,t"


class TestGetReplacer:
    def test_returns_replacement(self):
        replacer = get_replacer({"x": "xy", "y": "xy"})
        assert replacer("x") == "xy"
        assert replacer("y") == "xy"
        assert replacer("z") == "z"

    def test_none_replace_dict_passthrough(self):
        replacer = get_replacer(None)
        assert replacer("anything") == "anything"
