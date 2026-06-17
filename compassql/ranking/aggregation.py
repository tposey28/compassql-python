from __future__ import annotations

NAME = "aggregationQuality"


def _fq_attr(fq, attr, default=None):
    if isinstance(fq, dict):
        return fq.get(attr, default)
    return getattr(fq, attr, default)


def score(spec_m, schema, opt) -> dict:
    feature = _aggregation_quality_feature(spec_m)
    return {"score": feature["score"], "features": [feature]}


def _aggregation_quality_feature(spec_m) -> dict:
    encodings = spec_m.get_encodings()

    if spec_m.is_aggregate():
        def is_raw_continuous(enc_q) -> bool:
            field = _fq_attr(enc_q, "field")
            ftype = _fq_attr(enc_q, "type")
            aggregate = _fq_attr(enc_q, "aggregate")
            bin_ = _fq_attr(enc_q, "bin")
            time_unit = _fq_attr(enc_q, "timeUnit")
            type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None
            if field is None:
                return False
            return (
                (type_str == "quantitative" and not bin_ and not aggregate) or
                (type_str == "temporal" and not time_unit)
            )

        if any(is_raw_continuous(e) for e in encodings):
            return {"type": NAME, "score": 0.1, "feature": "Aggregate with raw continuous"}

        def is_dimension(enc_q) -> bool:
            field = _fq_attr(enc_q, "field")
            aggregate = _fq_attr(enc_q, "aggregate")
            auto_count = _fq_attr(enc_q, "autoCount")
            return auto_count or (field is not None and not aggregate)

        def is_field_q(enc_q) -> bool:
            return _fq_attr(enc_q, "field") is not None

        if any(is_field_q(e) and is_dimension(e) for e in encodings):
            has_count = any(
                (is_field_q(e) and _fq_attr(e, "aggregate") == "count") or
                _fq_attr(e, "autoCount")
                for e in encodings
            )
            has_bin = any(
                is_field_q(e) and bool(_fq_attr(e, "bin"))
                for e in encodings
            )
            if has_count:
                return {"type": NAME, "score": 0.8, "feature": "Aggregate with count"}
            elif has_bin:
                return {"type": NAME, "score": 0.7, "feature": "Aggregate with bin but without count"}
            else:
                return {"type": NAME, "score": 0.9, "feature": "Aggregate without count and without bin"}

        return {"type": NAME, "score": 0.3, "feature": "Aggregate without dimension"}
    else:
        def is_measure(enc_q) -> bool:
            field = _fq_attr(enc_q, "field")
            ftype = _fq_attr(enc_q, "type")
            bin_ = _fq_attr(enc_q, "bin")
            type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None
            if field is None:
                return False
            # isDimension is False when it's Q without bin, or T without timeUnit
            return type_str in ("quantitative",) and not bin_

        if any(_fq_attr(e, "field") is not None and not _is_dimension_enc(e) for e in encodings):
            return {"type": NAME, "score": 1.0, "feature": "Raw with measure"}
        return {"type": NAME, "score": 0.2, "feature": "Raw without measure"}


def _is_dimension_enc(enc_q) -> bool:
    field = _fq_attr(enc_q, "field")
    ftype = _fq_attr(enc_q, "type")
    aggregate = _fq_attr(enc_q, "aggregate")
    bin_ = _fq_attr(enc_q, "bin")
    time_unit = _fq_attr(enc_q, "timeUnit")
    type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None
    auto_count = _fq_attr(enc_q, "autoCount")

    if auto_count:
        return True
    if field is None:
        return False
    # A field is a measure if it's Q (no bin, no agg) or T (no timeUnit) — those are NOT dimensions
    if type_str == "quantitative" and not bin_ and not aggregate:
        return False
    if type_str == "temporal" and not time_unit:
        return False
    return True
