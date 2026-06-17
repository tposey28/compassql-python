from __future__ import annotations

from typing import Any, Optional

from compassql.propindex import PropIndex
from compassql.property import Property, is_encoding_property
from compassql.wildcard import Wildcard, is_wildcard


class WildcardIndex:
    """Tracks which properties in a SpecQuery are wildcards."""

    def __init__(self) -> None:
        self._mark: Optional[Wildcard] = None
        self._encodings: dict[int, PropIndex] = {}
        self._encoding_indices_by_property: PropIndex[list[int]] = PropIndex()

    def set_mark(self, wildcard: Wildcard) -> "WildcardIndex":
        self._mark = wildcard
        return self

    @property
    def mark(self) -> Optional[Wildcard]:
        return self._mark

    @property
    def encodings(self) -> dict[int, PropIndex]:
        return self._encodings

    @property
    def encoding_indices_by_property(self) -> PropIndex[list[int]]:
        return self._encoding_indices_by_property

    def set_encoding_property(self, index: int, prop: Property, wildcard: Wildcard) -> "WildcardIndex":
        enc_index = self._encodings.setdefault(index, PropIndex())
        enc_index.set(prop, wildcard)

        indices = self._encoding_indices_by_property.get(prop)
        if indices is None:
            indices = []
            self._encoding_indices_by_property.set(prop, indices)
        indices.append(index)
        return self

    def has_encoding_property(self, index: int, prop: Property) -> bool:
        enc = self._encodings.get(index)
        return enc is not None and enc.has(prop)

    def has_property(self, prop: Property) -> bool:
        if is_encoding_property(prop):
            return self._encoding_indices_by_property.has(prop)
        if prop == "mark":
            return self._mark is not None
        raise ValueError(f"Unimplemented for property {prop}")

    def is_empty(self) -> bool:
        return self._mark is None and self._encoding_indices_by_property.size() == 0

    @classmethod
    def build(cls, spec_q: dict, opt: Any = None) -> "WildcardIndex":
        """Build WildcardIndex from a SpecQuery dict by scanning for wildcard values."""
        from compassql.wildcard import is_wildcard, init_wildcard, DEFAULT_ENUM_INDEX, DEFAULT_NAME
        from compassql.property import (
            ENCODING_TOPLEVEL_PROPS, ENCODING_NESTED_PROP_PARENTS,
            get_encoding_nested_prop,
        )

        idx = cls()

        # Check mark
        mark = spec_q.get("mark")
        if is_wildcard(mark):
            wc = init_wildcard(
                mark,
                DEFAULT_NAME["mark"],
                DEFAULT_ENUM_INDEX["mark"],
            )
            idx.set_mark(wc)

        # Check encodings
        encodings = spec_q.get("encodings", [])
        for i, enc_q in enumerate(encodings):
            if not isinstance(enc_q, dict):
                continue
            for prop_name in ENCODING_TOPLEVEL_PROPS:
                val = enc_q.get(prop_name)
                if is_wildcard(val):
                    enum_key = prop_name
                    default_enum = (
                        (opt.enum if opt and opt.enum else DEFAULT_ENUM_INDEX).get(enum_key, [])
                    )
                    default_name = DEFAULT_NAME.get(prop_name, prop_name)
                    wc = init_wildcard(val, default_name, default_enum)
                    idx.set_encoding_property(i, prop_name, wc)

            # Check nested props (bin, scale, sort, axis, legend)
            for parent in ENCODING_NESTED_PROP_PARENTS:
                parent_val = enc_q.get(parent)
                if isinstance(parent_val, dict):
                    props_key = f"{parent}Props"
                    parent_enum = (opt.enum if opt and opt.enum else DEFAULT_ENUM_INDEX).get(props_key, {})
                    for child, child_val in parent_val.items():
                        if is_wildcard(child_val):
                            nested_prop = get_encoding_nested_prop(parent, child)
                            default_enum = parent_enum.get(child, [])
                            parent_short = DEFAULT_NAME.get(parent, parent)
                            parent_props_map = DEFAULT_NAME.get(f"{parent}Props", {})
                            child_short = parent_props_map.get(child, child)
                            default_name = f"{parent_short}-{child_short}"
                            wc = init_wildcard(child_val, default_name, default_enum)
                            idx.set_encoding_property(i, nested_prop, wc)

        return idx
