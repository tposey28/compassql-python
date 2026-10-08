from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from compassql.propindex import PropIndex
from compassql.wildcard import is_wildcard


@dataclass
class AbstractConstraint:
    name_: str
    description: str
    properties: list
    allow_wildcard_for_properties: bool
    strict_: bool


_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def config_field_name(constraint_name: str) -> str:
    """Map an upstream camelCase constraint name to its QueryConfig field.

    Constraint names mirror the TypeScript original (`omitRepeatedField`)
    while QueryConfig fields are snake_case (`omit_repeated_field`).
    tests/constraint/test_spec.py asserts every non-strict constraint has a
    config field under exactly this transformation.
    """
    return _CAMEL_BOUNDARY.sub("_", constraint_name).lower()


def constraint_enabled(constraint, opt) -> bool:
    """Whether a constraint should run: strict ones always, others per config."""
    if constraint.strict():
        return True
    return bool(getattr(opt, config_field_name(constraint.name()), False))


class AbstractConstraintModel(ABC):
    def __init__(self, constraint: AbstractConstraint):
        self._c = constraint

    def name(self) -> str:
        return self._c.name_

    def description(self) -> str:
        return self._c.description

    def properties(self) -> list:
        return self._c.properties

    def strict(self) -> bool:
        return self._c.strict_


class EncodingConstraintModel(AbstractConstraintModel):
    def __init__(self, constraint: AbstractConstraint, checker: Callable):
        super().__init__(constraint)
        self._checker = checker

    def has_all_required_properties_specific(self, enc_q) -> bool:
        from compassql.query.encoding import encoding_query_from_dict
        if isinstance(enc_q, dict):
            enc_q = encoding_query_from_dict(enc_q)
        for prop in self._c.properties:
            nested_parent = getattr(prop, "parent", None)
            nested_child = getattr(prop, "child", None)
            prop_key = prop if isinstance(prop, str) else None

            if nested_parent is not None:
                parent_val = getattr(enc_q, nested_parent, None)
                if parent_val is None:
                    continue
                child_val = parent_val.get(nested_child) if isinstance(parent_val, dict) else getattr(parent_val, nested_child, None)
                if child_val is not None and is_wildcard(child_val):
                    return False
            else:
                val = getattr(enc_q, prop_key, None)
                if val is not None and is_wildcard(val):
                    return False
        return True

    def satisfy(self, enc_q, schema, enc_wc_index: PropIndex, opt) -> bool:
        from compassql.query.encoding import encoding_query_from_dict
        if isinstance(enc_q, dict):
            enc_q = encoding_query_from_dict(enc_q)
        if not self._c.allow_wildcard_for_properties:
            if not self.has_all_required_properties_specific(enc_q):
                return True  # can't check yet, skip
        return self._checker(enc_q, schema, enc_wc_index, opt)
