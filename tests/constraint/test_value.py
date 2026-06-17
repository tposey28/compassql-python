"""Port of test/constraint/value.test.ts"""
from __future__ import annotations

from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.constraint.value import VALUE_CONSTRAINT_INDEX
from compassql.propindex import PropIndex
from tests.fixture import schema

CONSTRAINT_MANUALLY_SPECIFIED_CONFIG = DEFAULT_QUERY_CONFIG.__class__(
    **{
        **{f: getattr(DEFAULT_QUERY_CONFIG, f) for f in DEFAULT_QUERY_CONFIG.__dataclass_fields__},
        "constraint_manually_specified_value": True,
    }
)


class TestValueConstraintChecks:
    def test_true_if_value_is_not_constant_channel(self):
        value_q = {"value": "color", "channel": "color"}
        assert VALUE_CONSTRAINT_INDEX["doesNotSupportConstantValue"].satisfy(
            value_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
        )

    def test_false_if_value_is_constant_channel(self):
        for channel in ("row", "column", "x", "y", "detail"):
            value_q = {"value": channel, "channel": channel}
            assert not VALUE_CONSTRAINT_INDEX["doesNotSupportConstantValue"].satisfy(
                value_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )
