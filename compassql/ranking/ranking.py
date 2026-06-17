from __future__ import annotations

from typing import Callable

from compassql.ranking.effectiveness import effectiveness
from compassql.ranking import aggregation, fieldorder

RankingFn = Callable  # (spec_m, schema, opt) -> dict

_registry: dict[str, RankingFn] = {}


def register(name: str, fn: RankingFn) -> None:
    _registry[name] = fn


def get_ranking_fn(name: str) -> RankingFn:
    return _registry[name]


def get_score(model, ranking_name: str, schema, opt) -> dict:
    cached = model.get_ranking_score(ranking_name)
    if cached is not None:
        return cached
    fn = get_ranking_fn(ranking_name)
    result = fn(model, schema, opt)
    model.set_ranking_score(ranking_name, result)
    return result


def _get_score_difference(names: list[str], m1, m2, schema, opt) -> float:
    for name in names:
        diff = get_score(m2, name, schema, opt)["score"] - get_score(m1, name, schema, opt)["score"]
        if diff != 0:
            return diff
    return 0.0


def comparator_factory(name, schema, opt):
    names = [name] if isinstance(name, str) else name
    return lambda m1, m2: _get_score_difference(names, m1, m2, schema, opt)


def group_comparator_factory(name, schema, opt):
    names = [name] if isinstance(name, str) else name

    def _cmp(g1, g2):
        m1 = _get_top_item(g1)
        m2 = _get_top_item(g2)
        if m1 is None or m2 is None:
            return 0
        return _get_score_difference(names, m1, m2, schema, opt)

    return _cmp


def _get_top_item(group):
    if isinstance(group, dict):
        items = group.get("items")
    else:
        items = getattr(group, "items", None)
    if not items:
        return None
    first = items[0]
    if isinstance(first, dict) and "items" in first:
        return _get_top_item(first)
    if not isinstance(first, dict) and hasattr(first, "items") and not callable(first.items):
        return _get_top_item(first)
    return first


def rank(group, query, schema, level: int):
    nest = getattr(query, "nest", None) or (query.get("nest") if isinstance(query, dict) else None)
    order_by = (getattr(query, "orderBy", None) or getattr(query, "order_by", None) or
                (query.get("orderBy") or query.get("order_by") if isinstance(query, dict) else None))
    choose_by = (getattr(query, "chooseBy", None) or getattr(query, "choose_by", None) or
                 (query.get("chooseBy") or query.get("choose_by") if isinstance(query, dict) else None))
    config = getattr(query, "config", None) or (query.get("config") if isinstance(query, dict) else None)

    if isinstance(group, dict):
        items = group.get("items", [])
    else:
        items = getattr(group, "items", [])

    if not nest or level == len(nest):
        order = order_by or choose_by
        if order:
            names = [order] if isinstance(order, str) else order
            from functools import cmp_to_key
            cmp = comparator_factory(names, schema, config)
            items.sort(key=cmp_to_key(cmp))
            if choose_by and len(items) > 1:
                del items[1:]
    else:
        for subgroup in items:
            if hasattr(subgroup, "items") or (isinstance(subgroup, dict) and "items" in subgroup):
                rank(subgroup, query, schema, level + 1)

        nest_level = nest[level]
        order_group_by = (
            getattr(nest_level, "orderGroupBy", None) or
            getattr(nest_level, "order_group_by", None) or
            (nest_level.get("orderGroupBy") or nest_level.get("order_group_by") if isinstance(nest_level, dict) else None)
        )
        if order_group_by:
            names = [order_group_by] if isinstance(order_group_by, str) else order_group_by
            from functools import cmp_to_key
            cmp = group_comparator_factory(names, schema, config)
            items.sort(key=cmp_to_key(cmp))

    return group


EFFECTIVENESS = "effectiveness"

register(EFFECTIVENESS, effectiveness)
register(aggregation.NAME, aggregation.score)
register(fieldorder.NAME, fieldorder.score)
