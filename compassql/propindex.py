from __future__ import annotations

from typing import Generic, Iterator, Optional, TypeVar

from compassql.property import Property, to_key

V = TypeVar("V")


class PropIndex(Generic[V]):
    def __init__(self, initial: Optional[dict[str, V]] = None) -> None:
        self._data: dict[str, V] = dict(initial) if initial else {}

    def has(self, p: Property) -> bool:
        return to_key(p) in self._data

    def get(self, p: Property) -> Optional[V]:
        return self._data.get(to_key(p))

    def set(self, p: Property, value: V) -> "PropIndex[V]":
        self._data[to_key(p)] = value
        return self

    def set_by_key(self, key: str, value: V) -> None:
        self._data[key] = value

    def map(self, f) -> "PropIndex":
        result: PropIndex = PropIndex()
        for k, v in self._data.items():
            result._data[k] = f(v)
        return result

    def size(self) -> int:
        return len(self._data)

    def keys(self) -> Iterator[str]:
        return iter(self._data.keys())

    def values(self) -> Iterator[V]:
        return iter(self._data.values())

    def __iter__(self) -> Iterator[V]:
        return iter(self._data.values())

    def __len__(self) -> int:
        return len(self._data)

    def duplicate(self) -> "PropIndex[V]":
        return PropIndex(self._data)
