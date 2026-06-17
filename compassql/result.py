from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class ResultTree(Generic[T]):
    name: str
    path: str
    items: list[Union["ResultTree[T]", T]] = field(default_factory=list)
    group_by: Any = None
    order_group_by: Optional[Union[str, list[str]]] = None


def is_result_tree(item: Any) -> bool:
    return isinstance(item, ResultTree)


def get_top_result_tree_item(result: ResultTree[T]) -> Optional[T]:
    if not result.items:
        return None
    top = result.items[0]
    while top is not None and is_result_tree(top):
        top = top.items[0] if top.items else None
    return top


def map_leaves(group: ResultTree[T], f: Callable[[T], U]) -> ResultTree[U]:
    new_items = []
    for item in group.items:
        if is_result_tree(item):
            new_items.append(map_leaves(item, f))
        else:
            new_items.append(f(item))
    return ResultTree(
        name=group.name,
        path=group.path,
        items=new_items,
        group_by=group.group_by,
        order_group_by=group.order_group_by,
    )
