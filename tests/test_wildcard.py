"""Unit tests for compassql.wildcard — ported from test/wildcard.test.ts."""
from __future__ import annotations

import sys
_venv = "/home/julsey/.virtualenvs/NIST-Discvr/lib/python3.12/site-packages"
if _venv not in sys.path:
    sys.path.insert(0, _venv)

import pytest
from compassql.wildcard import (
    Wildcard,
    SHORT_WILDCARD,
    is_wildcard,
    is_short_wildcard,
    init_wildcard,
)
from compassql.property import DEFAULT_PROP_PRECEDENCE


class TestIsWildcard:
    def test_true_for_wildcard_with_name_and_enum(self):
        assert is_wildcard(Wildcard(name="a", enum=[1, 2, 3]))

    def test_true_for_wildcard_dict_with_name_and_enum(self):
        assert is_wildcard({"name": "a", "enum": [1, 2, 3]})

    def test_true_for_wildcard_with_name_only(self):
        assert is_wildcard(Wildcard(name="a"))

    def test_true_for_wildcard_with_enum_only(self):
        assert is_wildcard(Wildcard(enum=[1, 2, 3]))

    def test_true_for_short_wildcard(self):
        assert is_wildcard(SHORT_WILDCARD)

    def test_false_for_string(self):
        assert not is_wildcard("string")

    def test_false_for_number(self):
        assert not is_wildcard(9)

    def test_false_for_boolean(self):
        assert not is_wildcard(True)

    def test_false_for_array(self):
        assert not is_wildcard([1, 2])

    def test_false_for_none(self):
        assert not is_wildcard(None)


class TestInitWildcard:
    def test_short_wildcard_uses_defaults(self):
        mark = init_wildcard(SHORT_WILDCARD, "m", ["point"])
        assert mark.name == "m"
        assert mark.enum == ["point"]

    def test_full_wildcard_preserves_enum(self):
        wc = init_wildcard(Wildcard(enum=[True, False]), "b1", [True, False])
        assert wc.enum == [True, False]
        assert wc.name == "b1"

    def test_dict_wildcard_with_enum(self):
        wc = init_wildcard({"enum": [True, False]}, "b1", [True, False])
        assert wc.enum == [True, False]
        assert wc.name == "b1"


class TestIsShortWildcard:
    def test_true_for_question_mark(self):
        assert is_short_wildcard(SHORT_WILDCARD)

    def test_false_for_other_string(self):
        assert not is_short_wildcard("foo")

    def test_false_for_wildcard_object(self):
        assert not is_short_wildcard(Wildcard(name="a", enum=[1]))


class TestDefaultPropPrecedence:
    def test_precedence_list_non_empty(self):
        assert len(DEFAULT_PROP_PRECEDENCE) > 0

    def test_mark_in_precedence(self):
        from compassql.property import Property
        assert Property.MARK in DEFAULT_PROP_PRECEDENCE or "mark" in DEFAULT_PROP_PRECEDENCE
