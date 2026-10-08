from __future__ import annotations

import warnings
from typing import Any, Mapping, Optional

from compassql.config import QueryConfig, DEFAULT_QUERY_CONFIG
from compassql.constraint.base import config_field_name
from compassql.query.normalize import normalize
from compassql.query.query import Query
from compassql.ranking.ranking import rank
from compassql.schema import Schema


def _config_source(config: Any) -> Mapping[str, Any]:
    return vars(config) if hasattr(config, "__dict__") else config


def _to_config_fields(source: Mapping[str, Any], unknown: list[str]) -> dict[str, Any]:
    """Map one config mapping onto QueryConfig field names.

    Upstream CompassQL spells query config keys in camelCase
    (``autoAddCount``) while QueryConfig fields are snake_case
    (``auto_add_count``), so accept either. If a source spells the same
    setting both ways, the snake_case field name wins: it names a field
    exactly, whereas the camelCase form only maps onto one by convention.
    Keys that match no field after normalization are collected in
    ``unknown`` so the caller can report them — dropping them silently
    hides settings that were never applied.
    """
    fields = QueryConfig.__dataclass_fields__
    normalized: dict[str, Any] = {}
    for key, value in source.items():
        if key in fields:
            normalized[key] = value
            continue
        field_name = config_field_name(key)
        if field_name in fields:
            if field_name not in source:
                normalized[field_name] = value
        else:
            unknown.append(key)
    return normalized


def recommend(q: Query, schema: Schema, config: Optional[QueryConfig] = None) -> dict:
    # Normalize and merge config
    q = normalize(q)

    merged_config = {**vars(DEFAULT_QUERY_CONFIG)}
    unknown_keys: list[str] = []
    if config is not None:
        merged_config.update(_to_config_fields(_config_source(config), unknown_keys))
    if q.config is not None:
        merged_config.update(_to_config_fields(_config_source(q.config), unknown_keys))

    if unknown_keys:
        warnings.warn(
            "ignoring unrecognized query config key(s): "
            + ", ".join(sorted(set(unknown_keys))),
            stacklevel=2,
        )

    q.config = QueryConfig(**merged_config)

    # Generate — lazy import to avoid circular deps
    from compassql.generate import generate
    answer_set = generate(q.spec, schema, q.config)

    # Nest
    from compassql.nest import nest as nest_fn
    nested_answer_set = nest_fn(answer_set, q.nest)

    # Rank
    result = rank(nested_answer_set, q, schema, 0)

    return {"query": q, "result": result}
