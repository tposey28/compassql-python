"""Encoding-level constraint checking dispatcher (ported from src/constraint/encoding.ts)."""
from __future__ import annotations

from typing import Optional

from compassql.constraint.base import constraint_enabled
from compassql.propindex import PropIndex
from compassql.query.encoding import is_value_query

# Stands in for a fully-specified encoding, which WildcardIndex.encodings holds
# no entry for. Checkers dereference the value (wc.has(...)), so a miss has to
# yield an empty index rather than None.
_NO_WILDCARDS = PropIndex()


def check_encoding(prop, wildcard, index: int, spec_m, schema, opt) -> Optional[str]:
    """Check all encoding constraints for the encoding at `index`.
    Returns violated constraint name or None.
    """
    from compassql.constraint.field import FIELD_CONSTRAINTS_BY_PROPERTY
    from compassql.constraint.value import VALUE_CONSTRAINTS_BY_PROPERTY

    enc_q = spec_m.get_encoding_query_by_index(index)
    enc_wc_index = spec_m.wildcard_index.encodings.get(index) or _NO_WILDCARDS

    for c in (FIELD_CONSTRAINTS_BY_PROPERTY.get(prop) or []):
        if constraint_enabled(c, opt):
            if not c.satisfy(enc_q, schema, enc_wc_index, opt):
                violated = f"(enc) {c.name()}"
                if getattr(opt, "verbose", False):
                    wc_name = wildcard.name if hasattr(wildcard, "name") else str(wildcard)
                    print(f"{violated} failed with {spec_m.to_shorthand()} for {wc_name}")
                return violated

    if is_value_query(enc_q):
        for c in (VALUE_CONSTRAINTS_BY_PROPERTY.get(prop) or []):
            if constraint_enabled(c, opt):
                if not c.satisfy(enc_q, schema, enc_wc_index, opt):
                    violated = f"(enc) {c.name()}"
                    if getattr(opt, "verbose", False):
                        wc_name = wildcard.name if hasattr(wildcard, "name") else str(wildcard)
                        print(f"{violated} failed with {spec_m.to_shorthand()} for {wc_name}")
                    return violated

    return None
