from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


@dataclass(frozen=True)
class EncodingNestedProp:
    parent: str
    child: str

    def __hash__(self) -> int:
        return hash((self.parent, self.child))

    def __str__(self) -> str:
        return f"{self.parent}.{self.child}"


Property = Union[str, EncodingNestedProp]

ENCODING_TOPLEVEL_PROPS: list[str] = [
    "channel",
    "aggregate",
    "autoCount",
    "bin",
    "timeUnit",
    "hasFn",
    "sort",
    "stack",
    "field",
    "type",
    "format",
    "scale",
    "axis",
    "legend",
    "value",
]

ENCODING_NESTED_PROP_PARENTS: list[str] = ["bin", "scale", "sort", "axis", "legend"]

BIN_CHILD_PROPS: list[str] = ["maxbins", "divide", "extent", "base", "step", "steps", "minstep"]
SORT_CHILD_PROPS: list[str] = ["field", "op", "order"]

# These are populated lazily from wildcard.py lists to avoid circular imports
def _make_nested_props(parent: str, children: list[str]) -> list[EncodingNestedProp]:
    return [EncodingNestedProp(parent=parent, child=c) for c in children]


BIN_PROPS: list[EncodingNestedProp] = _make_nested_props("bin", BIN_CHILD_PROPS)
SORT_PROPS: list[EncodingNestedProp] = _make_nested_props("sort", SORT_CHILD_PROPS)

# Import scale/axis/legend property lists from wildcard to avoid duplication
from compassql.wildcard import SCALE_PROPERTIES, AXIS_PROPERTIES, LEGEND_PROPERTIES  # noqa: E402

SCALE_PROPS: list[EncodingNestedProp] = _make_nested_props("scale", SCALE_PROPERTIES)
AXIS_PROPS: list[EncodingNestedProp] = _make_nested_props("axis", AXIS_PROPERTIES)
LEGEND_PROPS: list[EncodingNestedProp] = _make_nested_props("legend", LEGEND_PROPERTIES)

ENCODING_NESTED_PROPS: list[EncodingNestedProp] = (
    BIN_PROPS + SORT_PROPS + SCALE_PROPS + AXIS_PROPS + LEGEND_PROPS
)

VIEW_PROPS: list[str] = ["width", "height", "background", "padding", "title"]

ALL_ENCODING_PROPS: list[Property] = list(ENCODING_TOPLEVEL_PROPS) + list(ENCODING_NESTED_PROPS)  # type: ignore[assignment]

# Index for fast nested prop lookup: {parent: {child: EncodingNestedProp}}
_ENCODING_NESTED_PROP_INDEX: dict[str, dict[str, EncodingNestedProp]] = {}
for _p in ENCODING_NESTED_PROPS:
    _ENCODING_NESTED_PROP_INDEX.setdefault(_p.parent, {})[_p.child] = _p


def is_encoding_nested_prop(p: Any) -> bool:
    return isinstance(p, EncodingNestedProp)


def is_encoding_toplevel_property(p: Any) -> bool:
    return isinstance(p, str) and p in ENCODING_TOPLEVEL_PROPS


def is_encoding_nested_parent(prop: str) -> bool:
    return prop in ENCODING_NESTED_PROP_PARENTS


def is_encoding_property(p: Any) -> bool:
    return is_encoding_toplevel_property(p) or is_encoding_nested_prop(p)


def get_encoding_nested_prop(parent: str, child: str) -> EncodingNestedProp:
    return (_ENCODING_NESTED_PROP_INDEX.get(parent) or {}).get(child) or EncodingNestedProp(parent=parent, child=child)


def to_key(p: Property) -> str:
    if isinstance(p, EncodingNestedProp):
        return f"{p.parent}.{p.child}"
    return str(p)


def from_key(k: str) -> Property:
    parts = k.split(".", 1)
    if len(parts) == 1:
        return k
    return EncodingNestedProp(parent=parts[0], child=parts[1])


DEFAULT_PROP_PRECEDENCE: list[Property] = (
    [
        "type",
        "field",
        "bin",
        "timeUnit",
        "aggregate",
        "autoCount",
        "channel",
        "mark",
        "stack",
        "scale",
        "sort",
        "axis",
        "legend",
    ]
    + BIN_PROPS  # type: ignore[operator]
    + SCALE_PROPS
    + AXIS_PROPS
    + LEGEND_PROPS
    + SORT_PROPS
)

# Namespace-style constants (mirrors TS `Property` namespace)
class Property:  # type: ignore[no-redef]
    MARK = "mark"
    TRANSFORM = "transform"
    STACK = "stack"
    FORMAT = "format"
    CHANNEL = "channel"
    AGGREGATE = "aggregate"
    AUTOCOUNT = "autoCount"
    BIN = "bin"
    HAS_FN = "hasFn"
    TIMEUNIT = "timeUnit"
    FIELD = "field"
    TYPE = "type"
    SORT = "sort"
    SCALE = "scale"
    AXIS = "axis"
    LEGEND = "legend"
    WIDTH = "width"
    HEIGHT = "height"
    BACKGROUND = "background"
    PADDING = "padding"
    TITLE = "title"
