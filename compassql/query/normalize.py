from __future__ import annotations

import copy

from compassql.query.query import Query
from compassql.query.groupby import Nest


def normalize(q: Query) -> Query:
    if q.groupBy is not None:
        nest = Nest(groupBy=q.groupBy)
        if q.orderBy is not None:
            nest.orderGroupBy = q.orderBy

        normalized = Query(
            spec=copy.deepcopy(q.spec),
            nest=[nest],
        )
        if q.chooseBy is not None:
            normalized.chooseBy = q.chooseBy
        if q.config is not None:
            normalized.config = q.config
        return normalized

    return copy.deepcopy(q)
