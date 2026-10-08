from __future__ import annotations

NAME = "fieldOrder"


def _fq_attr(fq, attr, default=None):
    return getattr(fq, attr, default)


def score(spec_m, schema, opt) -> dict:
    wc_index = spec_m.wildcard_index
    field_wc_indices = wc_index.encoding_indices_by_property.get("field") if wc_index else None

    if not field_wc_indices:
        return {"score": 0, "features": []}

    encodings = spec_m.get_encodings()
    num_fields = len(schema.field_schemas)

    features = []
    total_score = 0.0
    base = 1

    for i in range(len(field_wc_indices) - 1, -1, -1):
        idx = field_wc_indices[i]
        encoding = encodings[idx]

        field = _fq_attr(encoding, "field")
        if field is None:
            continue

        enc_wildcards = wc_index.encodings.get(idx)
        field_wc = enc_wildcards.get("field") if enc_wildcards else None
        field_schema = schema.field_schema(field)
        if field_schema is None:
            continue

        field_index = field_schema.index
        sc = -field_index * base
        total_score += sc

        wc_name = field_wc.name if field_wc and hasattr(field_wc, "name") else str(field)
        features.append({
            "score": sc,
            "type": "fieldOrder",
            "feature": f"field {wc_name} is {field} (#{field_index} in the schema)",
        })

        base *= num_fields

    return {"score": total_score, "features": features}
