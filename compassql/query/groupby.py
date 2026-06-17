from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from compassql.propindex import PropIndex
from compassql.property import Property


@dataclass
class ExtendedGroupBy:
    property: str
    replace: Optional[dict[str, str]] = None


def is_extended_group_by(g: Any) -> bool:
    if isinstance(g, ExtendedGroupBy):
        return True
    if isinstance(g, dict):
        return bool(g.get("property"))
    return False


GroupBy = Union[str, list[Union[str, ExtendedGroupBy]]]


@dataclass
class Nest:
    groupBy: GroupBy
    orderGroupBy: Optional[Union[str, list[str]]] = None


REPLACE_BLANK_FIELDS: dict[str, str] = {"*": ""}
REPLACE_XY_CHANNELS: dict[str, str] = {"x": "xy", "y": "xy"}
REPLACE_FACET_CHANNELS: dict[str, str] = {"row": "facet", "column": "facet"}
REPLACE_MARK_STYLE_CHANNELS: dict[str, str] = {
    "color": "style",
    "opacity": "style",
    "shape": "style",
    "size": "style",
}

GROUP_BY_FIELD_TRANSFORM: list[str] = [
    Property.FIELD,
    Property.TYPE,
    Property.AGGREGATE,
    Property.BIN,
    Property.TIMEUNIT,
    Property.STACK,
]

GROUP_BY_ENCODING: list[Union[str, ExtendedGroupBy]] = list(GROUP_BY_FIELD_TRANSFORM) + [
    ExtendedGroupBy(
        property=Property.CHANNEL,
        replace={
            "x": "xy", "y": "xy",
            "color": "style", "size": "style",
            "shape": "style", "opacity": "style",
            "row": "facet", "column": "facet",
        },
    )
]


def parse_group_by(
    group_by: list[Union[str, ExtendedGroupBy]],
    include: Optional[PropIndex[bool]] = None,
    replace_index: Optional[PropIndex[dict[str, str]]] = None,
) -> dict[str, Any]:
    from compassql.query.shorthand import get_replacer_index

    include = include or PropIndex()
    replace_index = replace_index or PropIndex()

    for grp_by in group_by:
        if is_extended_group_by(grp_by):
            prop = grp_by.property if isinstance(grp_by, ExtendedGroupBy) else grp_by["property"]
            repl = grp_by.replace if isinstance(grp_by, ExtendedGroupBy) else grp_by.get("replace")
            include.set_by_key(prop, True)
            replace_index.set_by_key(prop, repl)
        else:
            include.set_by_key(str(grp_by), True)

    return {
        "include": include,
        "replaceIndex": replace_index,
        "replacer": get_replacer_index(replace_index),
    }


def group_by_to_string(group_by: GroupBy) -> str:
    if isinstance(group_by, list):
        parts = []
        for g in group_by:
            if is_extended_group_by(g):
                prop = g.property if isinstance(g, ExtendedGroupBy) else g["property"]
                repl = g.replace if isinstance(g, ExtendedGroupBy) else g.get("replace")
                if repl:
                    replace_idx: dict[str, list[str]] = {}
                    for val_from, val_to in repl.items():
                        replace_idx.setdefault(val_to, []).append(val_from)
                    inner = ";".join(
                        f"{','.join(sorted(vfs))}=>{vt}"
                        for vt, vfs in sorted(replace_idx.items())
                    )
                    parts.append(f"{prop}[{inner}]")
                else:
                    parts.append(prop)
            else:
                parts.append(str(g))
        return ",".join(parts)
    return str(group_by)
