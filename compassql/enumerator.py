from __future__ import annotations

from typing import Any, Callable, Generator, Optional

from compassql.property import (
    Property,
    ENCODING_TOPLEVEL_PROPS,
    ENCODING_NESTED_PROPS,
)
from compassql.propindex import PropIndex
from compassql.wildcard import is_wildcard
from compassql.query.encoding import is_value_query, is_disabled_auto_count_query

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# An Enumerator takes a SpecQueryModel and yields candidate SpecQueryModels
Enumerator = Callable[["SpecQueryModel"], Generator["SpecQueryModel", None, None]]

# An EnumeratorFactory produces an Enumerator given wildcard_index, schema, opt
EnumeratorFactory = Callable[["WildcardIndex", "Schema", Any], Enumerator]

_ENUMERATOR_INDEX: PropIndex[EnumeratorFactory] = PropIndex()


def get_enumerator(prop: Any) -> Optional[EnumeratorFactory]:
    return _ENUMERATOR_INDEX.get(prop)


# ---------------------------------------------------------------------------
# Mark enumerator
# ---------------------------------------------------------------------------

def _mark_enumerator_factory(wildcard_index: Any, schema: Any, opt: Any) -> Enumerator:
    from compassql.constraint.spec import check_spec

    def _enumerate(spec_m: Any) -> Generator[Any, None, None]:
        mark_wildcard = spec_m.get_mark()
        for mark in mark_wildcard.enum:
            spec_m.set_mark(mark)
            if not check_spec("mark", wildcard_index.mark, spec_m, schema, opt):
                yield spec_m.duplicate()
        spec_m.reset_mark()

    return _enumerate


_ENUMERATOR_INDEX.set(Property.MARK, _mark_enumerator_factory)


# ---------------------------------------------------------------------------
# Encoding property enumerator factory
# ---------------------------------------------------------------------------

def encoding_property_enumerator_factory(prop: Any) -> EnumeratorFactory:
    def factory(wildcard_index: Any, schema: Any, opt: Any) -> Enumerator:
        from compassql.constraint.encoding import check_encoding
        from compassql.constraint.spec import check_spec

        def _enumerate(spec_m: Any) -> Generator[Any, None, None]:
            indices = wildcard_index.encoding_indices_by_property.get(prop)
            if not indices:
                yield spec_m.duplicate()
                return

            def recurse(job_index: int) -> Generator[Any, None, None]:
                if job_index == len(indices):
                    yield spec_m.duplicate()
                    return

                index = indices[job_index]
                wildcard = wildcard_index.encodings[index].get(prop)
                enc_q = spec_m.get_encoding_query_by_index(index)
                prop_wildcard = spec_m.get_encoding_property(index, prop)

                if (
                    is_value_query(enc_q)
                    or is_disabled_auto_count_query(enc_q)
                    or not prop_wildcard
                ):
                    yield from recurse(job_index + 1)
                else:
                    for prop_val in wildcard.enum:
                        if prop_val is None:
                            prop_val = None  # JSON null → Python None
                        spec_m.set_encoding_property(index, prop, prop_val, wildcard)

                        if check_encoding(prop, wildcard, index, spec_m, schema, opt):
                            continue
                        if check_spec(prop, wildcard, spec_m, schema, opt):
                            continue

                        yield from recurse(job_index + 1)

                    spec_m.reset_encoding_property(index, prop, wildcard)

            yield from recurse(0)

        return _enumerate

    return factory


# Register all encoding top-level and nested props
for _prop in ENCODING_TOPLEVEL_PROPS:
    _ENUMERATOR_INDEX.set(_prop, encoding_property_enumerator_factory(_prop))

for _nested_prop in ENCODING_NESTED_PROPS:
    _ENUMERATOR_INDEX.set(_nested_prop, encoding_property_enumerator_factory(_nested_prop))
