from __future__ import annotations

import copy
from typing import Optional

from compassql.config import QueryConfig, DEFAULT_QUERY_CONFIG
from compassql.query.normalize import normalize
from compassql.query.query import Query
from compassql.ranking.ranking import rank
from compassql.schema import Schema


def recommend(q: Query, schema: Schema, config: Optional[QueryConfig] = None) -> dict:
    # Normalize and merge config
    q = normalize(q)

    merged_config = {**vars(DEFAULT_QUERY_CONFIG)}
    if config is not None:
        merged_config.update(vars(config) if hasattr(config, "__dict__") else config)
    if q.config is not None:
        q_config = vars(q.config) if hasattr(q.config, "__dict__") else q.config
        merged_config.update(q_config)

    q.config = QueryConfig(**{k: v for k, v in merged_config.items() if k in QueryConfig.__dataclass_fields__})

    # Generate — lazy import to avoid circular deps
    from compassql.generate import generate
    answer_set = generate(q.spec, schema, q.config)

    # Nest
    from compassql.nest import nest as nest_fn
    nested_answer_set = nest_fn(answer_set, q.nest)

    # Rank
    result = rank(nested_answer_set, q, schema, 0)

    return {"query": q, "result": result}
