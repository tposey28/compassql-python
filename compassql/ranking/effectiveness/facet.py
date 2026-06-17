from __future__ import annotations

from compassql.ranking.effectiveness.base import Scorer


def _fq_attr(fq, attr, default=None):
    if isinstance(fq, dict):
        return fq.get(attr, default)
    return getattr(fq, attr, default)


class FacetScorer(Scorer):
    def __init__(self, opt=None):
        self._opt = opt or {}
        super().__init__("Facet")

    def _init_score(self) -> dict[str, float]:
        opt = self._opt
        pref = getattr(opt, "preferred_facet", None) if hasattr(opt, "preferred_facet") else opt.get("preferred_facet")
        score: dict[str, float] = {}
        if pref == "row":
            score["column"] = -0.01
        elif pref == "column":
            score["row"] = -0.01
        return score

    def get_score(self, spec_m, schema, opt) -> list[dict]:
        features = []
        for enc_q in spec_m.get_encodings():
            auto_count = _fq_attr(enc_q, "autoCount")
            field = _fq_attr(enc_q, "field")
            if field is not None or auto_count:
                channel = _fq_attr(enc_q, "channel")
                channel_str = channel.value if hasattr(channel, "value") else str(channel) if channel else ""
                fs = self._get_feature_score(channel_str)
                if fs:
                    features.append(fs)
        return features
