from __future__ import annotations

from compassql.ranking.effectiveness.base import Scorer


def _fq_attr(fq, attr, default=None):
    if isinstance(fq, dict):
        return fq.get(attr, default)
    return getattr(fq, attr, default)


class DimensionScorer(Scorer):
    def __init__(self):
        super().__init__("Dimension")

    def _init_score(self) -> dict[str, float]:
        return {
            "row": -2.0,
            "column": -2.0,
            "color": 0.0,
            "opacity": 0.0,
            "size": 0.0,
            "shape": 0.0,
        }

    def get_score(self, spec_m, schema, opt) -> list[dict]:
        if not spec_m.is_aggregate():
            return []

        max_fscore = {"type": "Dimension", "feature": "No Dimension", "score": -5.0}
        for enc_q in spec_m.get_encodings():
            auto_count = _fq_attr(enc_q, "autoCount")
            aggregate = _fq_attr(enc_q, "aggregate")
            field = _fq_attr(enc_q, "field")
            # isDimension: autoCount or (fieldQuery and not aggregate)
            if auto_count or (field is not None and not aggregate):
                channel = _fq_attr(enc_q, "channel")
                channel_str = channel.value if hasattr(channel, "value") else str(channel) if channel else ""
                fs = self._get_feature_score(channel_str)
                if fs and fs["score"] > max_fscore["score"]:
                    max_fscore = fs

        # DimensionScorer doesn't push features into the list in the TS source —
        # it only computes the max and returns [] (the reduce never pushes to features).
        # This matches the TS behavior: getScore returns [].
        return []
