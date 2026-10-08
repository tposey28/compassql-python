from __future__ import annotations

import json
from typing import Any, Callable, Optional, Union

from compassql.propindex import PropIndex
from compassql.property import Property
from compassql.query.groupby import (
    GROUP_BY_ENCODING,
    GROUP_BY_FIELD_TRANSFORM,
    Nest,
    parse_group_by,
)
from compassql.query.shorthand import spec as spec_shorthand
from compassql.query.spec import SpecQuery
from compassql.result import ResultTree

# Constant group-by keys
FIELD = "field"
FIELD_TRANSFORM = "fieldTransform"
ENCODING = "encoding"
SPEC = "spec"

# Registry mapping group name → key function
_group_registry: dict[str, Callable[[SpecQuery], str]] = {}


def register_key_fn(name: str, key_fn: Callable[[SpecQuery], str]) -> None:
    _group_registry[name] = key_fn


def get_group_by_key(spec_q: SpecQuery, group_by: str) -> str:
    return _group_registry[group_by](spec_q)


def nest(spec_models: list, query_nest: Optional[list[Nest]]) -> ResultTree:
    """Group spec models into a ResultTree hierarchy."""
    if query_nest:
        root_group: ResultTree = ResultTree(name="", path="", items=[])
        group_index: dict[str, ResultTree] = {}

        includes: list[PropIndex] = []
        replaces: list[PropIndex] = []
        replacers: list[Any] = []

        for l, nest_level in enumerate(query_nest):
            includes.append(includes[l - 1].duplicate() if l > 0 else PropIndex())
            replaces.append(replaces[l - 1].duplicate() if l > 0 else PropIndex())

            group_by = nest_level.groupBy
            if isinstance(group_by, list):
                parsed = parse_group_by(group_by, includes[l], replaces[l])
                replacers.append(parsed["replacer"])
            else:
                replacers.append(None)

        for spec_m in spec_models:
            path = ""
            group: ResultTree = root_group
            for l, nest_level in enumerate(query_nest):
                group_by = nest_level.groupBy
                group.group_by = group_by
                group.order_group_by = nest_level.orderGroupBy

                if isinstance(group_by, list):
                    key = spec_shorthand(spec_m.spec_query, includes[l], replacers[l])
                else:
                    key = _group_registry[group_by](spec_m.spec_query)

                path += f"/{key}"
                if path not in group_index:
                    new_group: ResultTree = ResultTree(name=key, path=path, items=[])
                    group_index[path] = new_group
                    group.items.append(new_group)
                group = group_index[path]

            group.items.append(spec_m)

        return root_group
    else:
        return ResultTree(name="", path="", items=list(spec_models))


# Register built-in key functions

_GROUP_BY_FIELD = [Property.FIELD]
_PARSED_GROUP_BY_FIELD = parse_group_by(_GROUP_BY_FIELD)

register_key_fn(FIELD, lambda spec_q: spec_shorthand(
    spec_q, _PARSED_GROUP_BY_FIELD["include"], _PARSED_GROUP_BY_FIELD["replacer"]
))

_PARSED_GROUP_BY_FIELD_TRANSFORM = parse_group_by(GROUP_BY_FIELD_TRANSFORM)

register_key_fn(FIELD_TRANSFORM, lambda spec_q: spec_shorthand(
    spec_q, _PARSED_GROUP_BY_FIELD_TRANSFORM["include"], _PARSED_GROUP_BY_FIELD_TRANSFORM["replacer"]
))

_PARSED_GROUP_BY_ENCODING = parse_group_by(GROUP_BY_ENCODING)

register_key_fn(ENCODING, lambda spec_q: spec_shorthand(
    spec_q, _PARSED_GROUP_BY_ENCODING["include"], _PARSED_GROUP_BY_ENCODING["replacer"]
))

register_key_fn(SPEC, lambda spec_q: json.dumps(
    spec_q.__dict__ if hasattr(spec_q, "__dict__") else spec_q,
    default=str,
    sort_keys=True,
))
