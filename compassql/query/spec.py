from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from compassql.wildcard import is_wildcard
from compassql.property import Property
from compassql.query.encoding import (
    EncodingQuery,
    is_disabled_auto_count_query,
    is_enabled_auto_count_query,
    is_field_query,
    to_encoding,
)
from compassql.query.transform import TransformQuery


@dataclass
class SpecQuery:
    mark: Any                              # WildcardProperty[Mark]
    encodings: list[EncodingQuery]
    data: Optional[dict[str, Any]] = None
    transform: Optional[list[TransformQuery]] = None
    width: Any = None
    height: Any = None
    background: Optional[str] = None
    padding: Any = None
    title: Any = None
    config: Optional[dict[str, Any]] = None


def from_spec(spec: dict[str, Any]) -> SpecQuery:
    from compassql.query.encoding import encoding_query_from_dict
    encodings: list[EncodingQuery] = []
    for channel, channel_def in (spec.get("encoding") or {}).items():
        props: dict[str, Any] = {"channel": channel}
        if isinstance(channel_def, dict):
            for prop, val in channel_def.items():
                if val is not None:
                    if prop in ("bin", "scale", "axis", "legend") and val is None:
                        props[prop] = False
                    else:
                        props[prop] = val
        if props.get("aggregate") == "count" and not props.get("field"):
            props["field"] = "*"
        encodings.append(encoding_query_from_dict(props))

    return SpecQuery(
        mark=spec.get("mark"),
        encodings=encodings,
        data=spec.get("data"),
        transform=spec.get("transform"),
        width=spec.get("width"),
        height=spec.get("height"),
        background=spec.get("background"),
        padding=spec.get("padding"),
        title=spec.get("title"),
        config=spec.get("config"),
    )


def is_aggregate(spec_q: SpecQuery) -> bool:
    for enc_q in spec_q.encodings:
        if is_field_query(enc_q):
            from compassql.query.encoding import _get
            agg = _get(enc_q, "aggregate")
            if agg and not is_wildcard(agg):
                return True
        if is_enabled_auto_count_query(enc_q):
            return True
    return False


def has_wildcard(spec_q: SpecQuery, exclude: Optional[list[Any]] = None) -> bool:
    from compassql.property import to_key
    exclude_keys: set[str] = {to_key(p) for p in (exclude or [])}

    if is_wildcard(spec_q.mark) and "mark" not in exclude_keys:
        return True

    for enc_q in spec_q.encodings:
        if _object_contains_wildcard(enc_q, exclude_keys):
            return True
    return False


def _object_contains_wildcard(obj: Any, exclude_keys: set[str] = frozenset()) -> bool:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return False
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in exclude_keys:
                continue
            if is_wildcard(v) or _object_contains_wildcard(v, exclude_keys):
                return True
        return False
    # dataclass
    try:
        obj_dict = obj.__dict__
    except AttributeError:
        return False
    for k, v in obj_dict.items():
        if k in exclude_keys:
            continue
        if is_wildcard(v) or _object_contains_wildcard(v, exclude_keys):
            return True
    return False


def get_stack_offset(spec_q: SpecQuery) -> Optional[str]:
    from compassql.query.encoding import _get
    for enc_q in spec_q.encodings:
        stack = _get(enc_q, "stack")
        if stack is not None and not is_wildcard(stack):
            return stack
    return None


def get_stack_channel(spec_q: SpecQuery) -> Optional[str]:
    from compassql.query.encoding import _get
    for enc_q in spec_q.encodings:
        stack = _get(enc_q, "stack")
        channel = _get(enc_q, "channel")
        if stack is not None and channel and not is_wildcard(channel):
            return channel
    return None


def has_required_stack_properties(spec_q: SpecQuery) -> bool:
    if is_wildcard(spec_q.mark):
        return False

    for enc_q in spec_q.encodings:
        if is_disabled_auto_count_query(enc_q):
            continue
        if _object_contains_wildcard(enc_q):
            return False
    return True
