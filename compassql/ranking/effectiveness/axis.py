from __future__ import annotations

from compassql.ranking.effectiveness.base import Scorer
from compassql.ranking.effectiveness.type import (
    BIN_Q, T, TIMEUNIT_T, TIMEUNIT_O, O, N, get_extended_type,
)


def _fq_attr(fq, attr, default=None):
    return getattr(fq, attr, default)


class AxisScorer(Scorer):
    def __init__(self, opt=None):
        self._opt = opt or {}
        super().__init__("Axis")

    def _init_score(self) -> dict[str, float]:
        opt = self._opt

        preferred_axes = [
            (BIN_Q, "preferred_bin_axis"),
            (T, "preferred_temporal_axis"),
            (TIMEUNIT_T, "preferred_temporal_axis"),
            (TIMEUNIT_O, "preferred_temporal_axis"),
            (O, "preferred_ordinal_axis"),
            (N, "preferred_nominal_axis"),
        ]

        score: dict[str, float] = {}
        for feature, opt_key in preferred_axes:
            pref = getattr(opt, opt_key, None) if hasattr(opt, opt_key) else opt.get(opt_key)
            if pref == "x":
                score[f"{feature.value}_y"] = -0.01
            elif pref == "y":
                score[f"{feature.value}_x"] = -0.01
        return score

    def featurize(self, ext_type, channel: str) -> str:
        type_str = ext_type.value if hasattr(ext_type, "value") else str(ext_type)
        return f"{type_str}_{channel}"

    def get_score(self, spec_m, schema, opt) -> list[dict]:
        features = []
        for enc_q in spec_m.get_encodings():
            auto_count = _fq_attr(enc_q, "autoCount")
            field = _fq_attr(enc_q, "field")
            if field is not None or auto_count:
                ext_type = get_extended_type(enc_q)
                channel = _fq_attr(enc_q, "channel")
                channel_str = channel.value if hasattr(channel, "value") else str(channel) if channel else ""
                feature = self.featurize(ext_type, channel_str)
                fs = self._get_feature_score(feature)
                if fs:
                    features.append(fs)
        return features
