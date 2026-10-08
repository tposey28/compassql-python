from __future__ import annotations

import copy
from typing import Any, Optional, Union

from compassql.config import QueryConfig
from compassql.property import (
    ENCODING_TOPLEVEL_PROPS,
    ENCODING_NESTED_PROPS,
    Property,
    is_encoding_nested_prop,
    is_encoding_nested_parent,
)
from compassql.query.encoding import (
    is_auto_count_query,
    is_disabled_auto_count_query,
    is_field_query,
    to_encoding,
)
from compassql.query.groupby import parse_group_by
from compassql.query.shorthand import spec as spec_shorthand
from compassql.query.spec import (
    SpecQuery,
    get_stack_channel,
    get_stack_offset,
    is_aggregate,
)
from compassql.result import ResultTree
from compassql.schema import Schema
from compassql.wildcard import (
    SHORT_WILDCARD,
    Wildcard,
    get_default_enum_values,
    get_default_name,
    init_wildcard,
    is_wildcard,
)
from compassql.wildcardindex import WildcardIndex


def _dict_to_spec_query(d: dict) -> SpecQuery:
    from compassql.query.encoding import encoding_query_from_dict
    raw = d.get("encodings", [])
    encodings = [encoding_query_from_dict(e) if isinstance(e, dict) else e for e in raw]
    return SpecQuery(
        mark=d.get("mark"),
        encodings=encodings,
        data=d.get("data"),
        transform=d.get("transform"),
        width=d.get("width"),
        height=d.get("height"),
        background=d.get("background"),
        padding=d.get("padding"),
        title=d.get("title"),
        config=d.get("config"),
    )


def _enc_get(enc_q: Any, attr: str) -> Any:
    return getattr(enc_q, attr, None)


def _enc_set(enc_q: Any, attr: str, value: Any) -> None:
    setattr(enc_q, attr, value)


def _copy_encoding(enc_q: Any) -> Any:
    """Shallow-copy an encoding dataclass, copying any dict-valued nested props."""
    c = copy.copy(enc_q)
    for attr in ("bin", "scale", "axis", "legend"):
        v = getattr(c, attr, None)
        if isinstance(v, dict):
            setattr(c, attr, dict(v))
    return c


class SpecQueryModel:
    """Wraps a SpecQuery and provides helpers for the enumeration process."""

    def __init__(
        self,
        spec: SpecQuery,
        wildcard_index: WildcardIndex,
        schema: Schema,
        opt: QueryConfig,
        wildcard_assignment: dict[str, Any],
    ) -> None:
        self._spec = spec
        self._wildcard_index = wildcard_index
        self._schema = schema
        self._opt = opt
        self._assigned_wildcard_index: dict[str, Any] = wildcard_assignment
        self._ranking_score: dict[str, Any] = {}

        # channel → count of encodings using that channel (excluding disabled autoCount)
        self._channel_field_count: dict[str, int] = {}
        for enc_q in spec.encodings:
            ch = _enc_get(enc_q, "channel")
            if not is_wildcard(ch) and not (is_auto_count_query(enc_q) and _enc_get(enc_q, "autoCount") is False):
                self._channel_field_count[str(ch)] = 1

    @classmethod
    def build(cls, spec_q: Any, schema: Schema, opt: QueryConfig) -> "SpecQueryModel":
        # Normalise dict input into a SpecQuery dataclass
        if isinstance(spec_q, dict):
            spec_q = _dict_to_spec_query(spec_q)

        wildcard_index = WildcardIndex()

        # Mark
        if is_wildcard(spec_q.mark):
            name = get_default_name("mark")
            spec_q.mark = init_wildcard(spec_q.mark, name, opt.enum.get("mark", []))
            wildcard_index.set_mark(spec_q.mark)

        for index, enc_q in enumerate(spec_q.encodings):
            if is_auto_count_query(enc_q):
                _enc_set(enc_q, "type", "quantitative")

            if is_field_query(enc_q) and _enc_get(enc_q, "type") is None:
                _enc_set(enc_q, "type", SHORT_WILDCARD)

            # Top-level encoding props
            for prop in ENCODING_TOPLEVEL_PROPS:
                val = _enc_get(enc_q, prop)
                if is_wildcard(val):
                    default_name = get_default_name(prop) + str(index)
                    default_enum = get_default_enum_values(prop, schema, opt)
                    wildcard = init_wildcard(val, default_name, default_enum)
                    _enc_set(enc_q, prop, wildcard)
                    wildcard_index.set_encoding_property(index, prop, wildcard)

            # Nested encoding props (bin.maxbins, scale.type, etc.)
            for nested_prop in ENCODING_NESTED_PROPS:
                parent = nested_prop.parent
                child = nested_prop.child
                parent_obj = _enc_get(enc_q, parent)
                if isinstance(parent_obj, dict) and is_wildcard(parent_obj.get(child)):
                    default_name = get_default_name(nested_prop) + str(index)
                    default_enum = get_default_enum_values(nested_prop, schema, opt)
                    wildcard = init_wildcard(parent_obj[child], default_name, default_enum)
                    parent_obj[child] = wildcard
                    wildcard_index.set_encoding_property(index, nested_prop, wildcard)

        # Auto-add count if configured
        if opt.auto_add_count:
            from compassql.query.encoding import AutoCountQuery
            enc_len = len(spec_q.encodings)
            channel_wc = Wildcard(
                name=get_default_name("channel") + str(enc_len),
                enum=get_default_enum_values("channel", schema, opt),
            )
            auto_count_wc = Wildcard(
                name=get_default_name("autoCount") + str(enc_len),
                enum=[False, True],
            )
            count_enc = AutoCountQuery(
                channel=channel_wc,
                autoCount=auto_count_wc,
                type="quantitative",
            )
            spec_q.encodings.append(count_enc)
            wildcard_index.set_encoding_property(enc_len, "channel", channel_wc)
            wildcard_index.set_encoding_property(enc_len, "autoCount", auto_count_wc)

        return cls(spec_q, wildcard_index, schema, opt, {})

    # ---- accessors ----

    @property
    def wildcard_index(self) -> WildcardIndex:
        return self._wildcard_index

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def spec_query(self) -> SpecQuery:
        return self._spec

    # ---- duplication ----

    def duplicate(self) -> "SpecQueryModel":
        spec_copy = SpecQuery(
            mark=self._spec.mark,
            encodings=[_copy_encoding(e) for e in self._spec.encodings],
            data=self._spec.data,
            transform=self._spec.transform,
            width=self._spec.width,
            height=self._spec.height,
            background=self._spec.background,
            padding=self._spec.padding,
            title=self._spec.title,
            config=self._spec.config,
        )
        return SpecQueryModel(spec_copy, self._wildcard_index, self._schema, self._opt, dict(self._assigned_wildcard_index))

    # ---- mark mutation ----

    def set_mark(self, mark: str) -> None:
        name = self._wildcard_index.mark.name
        self._assigned_wildcard_index[name] = mark
        self._spec.mark = mark

    def reset_mark(self) -> None:
        wildcard = self._wildcard_index.mark
        self._spec.mark = wildcard
        self._assigned_wildcard_index.pop(wildcard.name, None)

    def get_mark(self) -> Any:
        return self._spec.mark

    # ---- encoding property mutation ----

    def get_encoding_property(self, index: int, prop: Property) -> Any:
        enc_q = self._spec.encodings[index]
        if is_encoding_nested_prop(prop):
            parent_obj = _enc_get(enc_q, prop.parent)
            return parent_obj.get(prop.child) if isinstance(parent_obj, dict) else None
        return _enc_get(enc_q, prop)

    def set_encoding_property(self, index: int, prop: Property, value: Any, wildcard: Wildcard) -> None:
        enc_q = self._spec.encodings[index]

        if prop == "channel":
            old_ch = _enc_get(enc_q, "channel")
            if not is_wildcard(old_ch):
                key = str(old_ch)
                self._channel_field_count[key] = max(0, self._channel_field_count.get(key, 0) - 1)

        if is_encoding_nested_prop(prop):
            parent_obj = _enc_get(enc_q, prop.parent)
            if isinstance(parent_obj, dict):
                parent_obj[prop.child] = value
        elif is_encoding_nested_parent(prop) and value is True:
            existing = _enc_get(enc_q, prop) or {}
            if isinstance(existing, dict):
                merged = {k: v for k, v in existing.items() if k not in ("enum", "name")}
                _enc_set(enc_q, prop, merged)
            else:
                _enc_set(enc_q, prop, {})
        else:
            _enc_set(enc_q, prop, value)

        self._assigned_wildcard_index[wildcard.name] = value

        if prop == "channel":
            self._channel_field_count[str(value)] = self._channel_field_count.get(str(value), 0) + 1

    def reset_encoding_property(self, index: int, prop: Property, wildcard: Wildcard) -> None:
        enc_q = self._spec.encodings[index]

        if prop == "channel":
            ch = _enc_get(enc_q, "channel")
            key = str(ch)
            self._channel_field_count[key] = max(0, self._channel_field_count.get(key, 0) - 1)

        if is_encoding_nested_prop(prop):
            parent_obj = _enc_get(enc_q, prop.parent)
            if isinstance(parent_obj, dict):
                parent_obj[prop.child] = wildcard
        else:
            _enc_set(enc_q, prop, wildcard)

        self._assigned_wildcard_index.pop(wildcard.name, None)

    # ---- channel helpers ----

    def channel_used(self, channel: str) -> bool:
        return self._channel_field_count.get(str(channel), 0) > 0

    def channel_encoding_field(self, channel: str) -> bool:
        enc_q = self.get_encoding_query_by_channel(channel)
        return enc_q is not None and is_field_query(enc_q)

    # ---- encoding accessors ----

    def get_encodings(self) -> list:
        return [e for e in self._spec.encodings if not is_disabled_auto_count_query(e)]

    def get_encoding_query_by_channel(self, channel: str) -> Optional[Any]:
        for enc_q in self._spec.encodings:
            if _enc_get(enc_q, "channel") == channel:
                return enc_q
        return None

    def get_encoding_query_by_index(self, i: int) -> Any:
        return self._spec.encodings[i]

    # ---- spec-level helpers ----

    def is_aggregate(self) -> bool:
        return is_aggregate(self._spec)

    def get_stack_offset(self) -> Optional[str]:
        return get_stack_offset(self._spec)

    def get_stack_channel(self) -> Optional[str]:
        return get_stack_channel(self._spec)

    # ---- shorthand ----

    def to_shorthand(self, group_by: Optional[Union[str, list]] = None) -> str:
        if group_by is not None:
            if isinstance(group_by, str):
                from compassql.nest import get_group_by_key
                return get_group_by_key(self._spec, group_by)
            parsed = parse_group_by(group_by)
            return spec_shorthand(self._spec, parsed.include, parsed.replacer)
        return spec_shorthand(self._spec)

    # ---- to_spec ----

    def to_spec(self, data: Optional[dict] = None) -> Optional[dict]:
        if is_wildcard(self._spec.mark):
            return None

        spec: dict = {}
        data = data or self._spec.data
        if data:
            spec["data"] = data

        if self._spec.transform:
            spec["transform"] = self._spec.transform

        spec["mark"] = self._spec.mark

        encoding = to_encoding(self._spec.encodings, {"schema": self._schema, "wildcardMode": "null"})
        if encoding is None:
            return None
        spec["encoding"] = encoding

        for attr in ("width", "height", "background", "padding", "title"):
            val = getattr(self._spec, attr, None)
            if val is not None:
                spec[attr] = val

        default_cfg = self._opt.default_spec_config if self._opt else None
        spec_config = getattr(self._spec, "config", None)
        if spec_config or default_cfg:
            merged_cfg: dict = {}
            if default_cfg:
                merged_cfg.update(default_cfg)
            if spec_config:
                merged_cfg.update(spec_config)
            spec["config"] = merged_cfg

        return spec

    # ---- ranking scores ----

    def get_ranking_score(self, ranking_name: str) -> Any:
        return self._ranking_score.get(ranking_name)

    def set_ranking_score(self, ranking_name: str, score: Any) -> None:
        self._ranking_score[ranking_name] = score


# Type alias
SpecQueryModelGroup = ResultTree[SpecQueryModel]
