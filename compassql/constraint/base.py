from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from compassql.propindex import PropIndex
from compassql.property import Property
from compassql.wildcard import is_wildcard


@dataclass
class AbstractConstraint:
    name_: str
    description: str
    properties: list
    allow_wildcard_for_properties: bool
    strict_: bool


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
        for prop in self._c.properties:
            prop_key = prop if isinstance(prop, str) else None
            nested_parent = getattr(prop, "parent", None)
            nested_child = getattr(prop, "child", None)

            if nested_parent is not None:
                parent_val = (
                    enc_q.get(nested_parent) if isinstance(enc_q, dict)
                    else getattr(enc_q, nested_parent, None)
                )
                if parent_val is None:
                    continue
                child_val = (
                    parent_val.get(nested_child) if isinstance(parent_val, dict)
                    else getattr(parent_val, nested_child, None)
                )
                if child_val is not None and is_wildcard(child_val):
                    return False
            else:
                val = (
                    enc_q.get(prop_key) if isinstance(enc_q, dict)
                    else getattr(enc_q, prop_key, None)
                )
                if val is not None and is_wildcard(val):
                    return False
        return True

    def satisfy(self, enc_q, schema, enc_wc_index: PropIndex, opt) -> bool:
        if not self._c.allow_wildcard_for_properties:
            if not self.has_all_required_properties_specific(enc_q):
                return True  # can't check yet, skip
        return self._checker(enc_q, schema, enc_wc_index, opt)
