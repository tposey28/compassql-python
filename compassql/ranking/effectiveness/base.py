from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class Scorer(ABC):
    def __init__(self, type_: str):
        self.type = type_
        self.score_index: dict[str, float] = self._init_score()

    @abstractmethod
    def _init_score(self) -> dict[str, float]: ...

    def _get_feature_score(self, feature: str) -> Optional[dict]:
        score = self.score_index.get(feature)
        if score is not None:
            return {"type": self.type, "feature": feature, "score": score}
        return None

    @abstractmethod
    def get_score(self, spec_m, schema, opt) -> list[dict]: ...
