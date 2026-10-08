from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from compassql.query.spec import SpecQuery, from_spec
from compassql.query.groupby import GroupBy, Nest


@dataclass
class Query:
    spec: SpecQuery
    groupBy: Optional[GroupBy] = None
    nest: Optional[list[Nest]] = None
    orderBy: Optional[Union[str, list[str]]] = None
    chooseBy: Optional[Union[str, list[str]]] = None
    config: Optional[Any] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Query":
        spec_dict = d.get("spec", {})
        spec_q = from_spec(spec_dict) if isinstance(spec_dict, dict) else spec_dict

        nest = None
        if "nest" in d:
            nest = []
            for n in d["nest"]:
                if isinstance(n, dict):
                    nest.append(Nest(
                        groupBy=n.get("groupBy"),
                        orderGroupBy=n.get("orderGroupBy"),
                    ))
                else:
                    nest.append(n)

        return cls(
            spec=spec_q,
            groupBy=d.get("groupBy"),
            nest=nest,
            orderBy=d.get("orderBy"),
            chooseBy=d.get("chooseBy"),
            config=d.get("config"),
        )
