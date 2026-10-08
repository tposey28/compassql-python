from __future__ import annotations

from compassql.constraint.base import AbstractConstraint, EncodingConstraintModel
from compassql.propindex import PropIndex
from compassql.property import Property


def _fq_attr(fq, attr, default=None):
    return getattr(fq, attr, default)


VALUE_CONSTRAINTS: list[EncodingConstraintModel] = [
    EncodingConstraintModel(
        AbstractConstraint(
            name_="doesNotSupportConstantValue",
            description="row, column, x, y, order, and detail should not work with constant values.",
            properties=[Property.TYPE, Property.AGGREGATE],
            allow_wildcard_for_properties=False,
            strict_=True,
        ),
        lambda value_q, schema, wc, opt: (
            _fq_attr(value_q, "channel") not in (
                "row", "column", "x", "y", "detail", "order"
            )
        ),
    ),
]

VALUE_CONSTRAINT_INDEX: dict[str, EncodingConstraintModel] = {
    c.name(): c for c in VALUE_CONSTRAINTS
}

VALUE_CONSTRAINTS_BY_PROPERTY: PropIndex = PropIndex()
for _c in VALUE_CONSTRAINTS:
    for _prop in _c._c.properties:
        _existing = VALUE_CONSTRAINTS_BY_PROPERTY.get(_prop) or []
        VALUE_CONSTRAINTS_BY_PROPERTY.set(_prop, _existing + [_c])
