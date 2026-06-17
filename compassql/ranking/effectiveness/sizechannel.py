from __future__ import annotations

from compassql.ranking.effectiveness.base import Scorer


def _fq_attr(fq, attr, default=None):
    return getattr(fq, attr, default)


class SizeChannelScorer(Scorer):
    def __init__(self):
        super().__init__("SizeChannel")

    def _init_score(self) -> dict[str, float]:
        return {
            "bar_size": -2.0,
            "tick_size": -2.0,
        }

    def get_score(self, spec_m, schema, opt) -> list[dict]:
        mark = spec_m.get_mark()
        mark_str = mark.value if hasattr(mark, "value") else str(mark) if mark else ""
        features = []
        for enc_q in spec_m.get_encodings():
            auto_count = _fq_attr(enc_q, "autoCount")
            field = _fq_attr(enc_q, "field")
            if field is not None or auto_count:
                channel = _fq_attr(enc_q, "channel")
                channel_str = channel.value if hasattr(channel, "value") else str(channel) if channel else ""
                feature = f"{mark_str}_{channel_str}"
                fs = self._get_feature_score(feature)
                if fs:
                    features.append(fs)
        return features
