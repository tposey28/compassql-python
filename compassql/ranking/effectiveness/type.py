from __future__ import annotations

from enum import Enum


class ExtendedType(str, Enum):
    Q = "quantitative"
    BIN_Q = "bin_quantitative"
    T = "temporal"
    TIMEUNIT_T = "timeUnit_time"
    TIMEUNIT_O = "timeUnit_ordinal"
    O = "ordinal"
    N = "nominal"
    K = "key"
    NONE = "-"


Q = ExtendedType.Q
BIN_Q = ExtendedType.BIN_Q
T = ExtendedType.T
TIMEUNIT_T = ExtendedType.TIMEUNIT_T
TIMEUNIT_O = ExtendedType.TIMEUNIT_O
O = ExtendedType.O
N = ExtendedType.N
K = ExtendedType.K
NONE = ExtendedType.NONE


def _fq_attr(fq, attr, default=None):
    if isinstance(fq, dict):
        return fq.get(attr, default)
    return getattr(fq, attr, default)


def get_extended_type(enc_q) -> ExtendedType:
    bin_ = _fq_attr(enc_q, "bin")
    time_unit = _fq_attr(enc_q, "timeUnit")
    ftype = _fq_attr(enc_q, "type")
    type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None

    if bin_:
        return ExtendedType.BIN_Q
    elif time_unit:
        # Check if scale has discrete domain — use a simple heuristic based on time unit
        try:
            from compassql.query.encoding import scale_type as get_scale_type
            from compassql.vegalite_types import has_discrete_domain
            s_type = get_scale_type(enc_q)
            if s_type is not None and has_discrete_domain(s_type):
                return ExtendedType.TIMEUNIT_O
        except Exception:
            pass
        return ExtendedType.TIMEUNIT_T

    if type_str == "quantitative":
        return ExtendedType.Q
    elif type_str == "temporal":
        return ExtendedType.T
    elif type_str == "ordinal":
        return ExtendedType.O
    elif type_str == "nominal":
        return ExtendedType.N
    elif type_str == "key":
        return ExtendedType.K
    return ExtendedType.NONE
