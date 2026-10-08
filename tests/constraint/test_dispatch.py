"""Coverage for the constraint dispatchers (check_spec / check_encoding).

The rest of tests/constraint/ exercises each constraint's checker directly via
SPEC_CONSTRAINT_INDEX[...].satisfy(...), which bypasses the dispatchers. That
left the config gate -- the step that decides whether a non-strict constraint
runs at all -- with no coverage, and a gate that silently disabled all 19
non-strict constraints passed the whole suite. These tests cover that step.
"""
from __future__ import annotations

import dataclasses

import pytest

from compassql.config import DEFAULT_QUERY_CONFIG, QueryConfig
from compassql.constraint.base import config_field_name, constraint_enabled
from compassql.constraint.encoding import check_encoding
from compassql.constraint.field import FIELD_CONSTRAINTS
from compassql.constraint.spec import (
    SPEC_CONSTRAINTS,
    SPEC_CONSTRAINT_INDEX,
    check_spec,
)
from compassql.model import SpecQueryModel
from compassql.property import Property
from tests.fixture import schema


def _config(**overrides) -> QueryConfig:
    """DEFAULT_QUERY_CONFIG with specific flags overridden."""
    base = {f: getattr(DEFAULT_QUERY_CONFIG, f) for f in DEFAULT_QUERY_CONFIG.__dataclass_fields__}
    base.update(overrides)
    return QueryConfig(**base)


class TestConfigFieldName:
    def test_maps_camel_case_to_snake_case(self):
        assert config_field_name("omitRepeatedField") == "omit_repeated_field"
        assert config_field_name("autoAddCount") == "auto_add_count"
        assert config_field_name("maxCardinalityForFacet") == "max_cardinality_for_facet"

    @pytest.mark.parametrize(
        "constraint",
        [c for c in (*SPEC_CONSTRAINTS, *FIELD_CONSTRAINTS) if not c.strict()],
        ids=lambda c: c.name(),
    )
    def test_every_non_strict_constraint_resolves_to_a_real_config_field(self, constraint):
        """The gate is only meaningful if the derived name actually exists."""
        assert hasattr(DEFAULT_QUERY_CONFIG, config_field_name(constraint.name()))


class TestConstraintEnabled:
    def test_strict_constraints_always_run(self):
        strict = next(c for c in SPEC_CONSTRAINTS if c.strict())
        # even against a config object carrying no flags at all
        assert constraint_enabled(strict, object()) is True

    @pytest.mark.parametrize(
        "constraint",
        [c for c in SPEC_CONSTRAINTS if not c.strict()],
        ids=lambda c: c.name(),
    )
    def test_non_strict_constraint_follows_its_config_flag(self, constraint):
        """Regression: a camelCase getattr misses the snake_case field and
        returns the False default, disabling every non-strict constraint."""
        field = config_field_name(constraint.name())
        assert constraint_enabled(constraint, _config(**{field: True})) is True
        assert constraint_enabled(constraint, _config(**{field: False})) is False

    def test_default_config_enables_the_constraints_it_declares_on(self):
        enabled = [
            c for c in SPEC_CONSTRAINTS
            if not c.strict() and constraint_enabled(c, DEFAULT_QUERY_CONFIG)
        ]
        # DEFAULT_QUERY_CONFIG turns several of these on; a broken gate yields 0.
        assert enabled, "no non-strict spec constraint is enabled under the default config"


class TestGateChangesEnumeration:
    """The gate's real job: deciding whether a non-strict constraint prunes.

    Driven through generate() because a non-strict constraint like
    omitRepeatedField only fires once a field has actually been *enumerated*
    from a wildcard -- which is exactly the path the dispatchers serve.
    """

    SPEC = {
        "mark": "point",
        "encodings": [
            {"channel": "?", "field": "?", "type": "quantitative"},
            {"channel": "?", "field": "?", "type": "quantitative"},
        ],
    }

    @staticmethod
    def _fields(model):
        out = []
        for enc in model.get_encodings():
            f = enc.get("field") if isinstance(enc, dict) else getattr(enc, "field", None)
            if f is not None:
                out.append(f)
        return out

    def _generate(self, **flags):
        from compassql.generate import generate
        return generate(self.SPEC, schema, _config(**flags))

    def test_repeated_fields_are_pruned_when_flag_is_on(self):
        answer = self._generate(omit_repeated_field=True)
        repeated = [m for m in answer if len(set(self._fields(m))) < len(self._fields(m))]
        assert repeated == [], f"{len(repeated)} specs reuse a field despite omitRepeatedField"

    def test_repeated_fields_survive_when_flag_is_off(self):
        answer = self._generate(omit_repeated_field=False)
        repeated = [m for m in answer if len(set(self._fields(m))) < len(self._fields(m))]
        assert repeated, "flag is off, so repeated-field specs should not be pruned"

    def test_flag_materially_shrinks_the_answer_set(self):
        """A dead gate lets every non-strict constraint through, which is
        visible as a far larger answer set."""
        on = len(self._generate(omit_repeated_field=True))
        off = len(self._generate(omit_repeated_field=False))
        assert on < off


class TestCheckEncodingGating:
    """typeMatchesSchemaType is non-strict and keyed to Property.FIELD/TYPE.

    The type must be the wildcard: check_encoding is only invoked for the
    property currently being enumerated, so a concrete type never reaches
    this constraint at all.
    """

    # N is nominal in the fixture schema
    SPEC = {
        "mark": "point",
        "encodings": [{"channel": "x", "field": "N", "type": "?"}],
    }

    def _types(self, **flags):
        from compassql.generate import generate
        answer = generate(self.SPEC, schema, _config(**flags))
        out = set()
        for m in answer:
            enc = m.get_encoding_query_by_index(0)
            t = enc.get("type") if isinstance(enc, dict) else getattr(enc, "type", None)
            out.add(t.value if hasattr(t, "value") else str(t))
        return out

    def test_only_the_schema_type_survives_when_flag_is_on(self):
        assert self._types(type_matches_schema_type=True) == {"nominal"}

    def test_mismatched_types_survive_when_flag_is_off(self):
        types = self._types(type_matches_schema_type=False)
        assert len(types) > 1, f"expected several enumerated types, got {types}"


class TestPinnedEncodings:
    """Encodings may be pinned concrete while others stay wildcards.

    This is how a caller narrows the search: fix what is already decided (say
    x = the independent column) and enumerate only the rest. WildcardIndex
    stores wildcards in a dict keyed by encoding index, holding entries only for
    encodings that have one -- so a pinned encoding leaves a gap. Indexing that
    dict as if it were a list yields None for the *later* encodings and crashes
    the constraint checkers that dereference it.
    """

    @staticmethod
    def _generate(spec, **flags):
        from compassql.generate import generate
        return generate(spec, schema, _config(**flags))

    def test_first_encoding_pinned_second_wildcard(self):
        answer = self._generate({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": "?", "field": "Q1", "type": "quantitative"},
            ],
        })
        assert answer

    def test_second_encoding_pinned_first_wildcard(self):
        answer = self._generate({
            "mark": "point",
            "encodings": [
                {"channel": "?", "field": "Q", "type": "quantitative"},
                {"channel": "y", "field": "Q1", "type": "quantitative"},
            ],
        })
        assert answer

    def test_pinned_encoding_alongside_enum_wildcards(self):
        """The regression case: pinning encoding 0 leaves index 1 unmapped, so a
        list-style lookup returns None and field constraints raise
        AttributeError on wc.has(...)."""
        answer = self._generate({
            "mark": "?",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": {"enum": ["y", "color"]},
                 "field": {"enum": ["Q1", "Q2"]},
                 "type": "quantitative"},
            ],
        })
        assert answer
        for model in answer:
            fields = [e.get("field") if isinstance(e, dict) else getattr(e, "field", None)
                      for e in model.get_encodings()]
            assert "Q" in fields

    def test_every_encoding_pinned(self):
        answer = self._generate({
            "mark": "?",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": "y", "field": "Q1", "type": "quantitative"},
            ],
        })
        assert answer

    def test_pinning_narrows_the_answer_set(self):
        """The point of pinning: far fewer candidates than the open search."""
        pinned = self._generate({
            "mark": "point",
            "encodings": [
                {"channel": "x", "field": "Q", "type": "quantitative"},
                {"channel": "?", "field": {"enum": ["Q1", "Q2"]}, "type": "quantitative"},
            ],
        })
        opened = self._generate({
            "mark": "point",
            "encodings": [
                {"channel": "?", "field": "?", "type": "quantitative"},
                {"channel": "?", "field": "?", "type": "quantitative"},
            ],
        })
        assert 0 < len(pinned) < len(opened)
