from __future__ import annotations

from compassql.ranking.effectiveness.base import Scorer
from compassql.ranking.effectiveness.type import ExtendedType, Q, T, BIN_Q, TIMEUNIT_T, TIMEUNIT_O, O, N, K, get_extended_type

TERRIBLE = -10.0


def _fq_attr(fq, attr, default=None):
    return getattr(fq, attr, default)


def _field_def_shorthand(enc_q) -> str:
    field = _fq_attr(enc_q, "field")
    ftype = _fq_attr(enc_q, "type")
    aggregate = _fq_attr(enc_q, "aggregate")
    bin_ = _fq_attr(enc_q, "bin")
    time_unit = _fq_attr(enc_q, "timeUnit")

    type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else "?"
    parts = []
    if aggregate:
        agg_str = aggregate.value if hasattr(aggregate, "value") else str(aggregate)
        parts.append(f"{agg_str}({field})")
    elif bin_:
        parts.append(f"bin({field})")
    elif time_unit:
        tu_str = time_unit.value if hasattr(time_unit, "value") else str(time_unit)
        parts.append(f"{tu_str}({field})")
    else:
        parts.append(str(field) if field else "?")
    parts.append(type_str)
    return ",".join(parts)


class TypeChannelScorer(Scorer):
    def __init__(self):
        super().__init__("TypeChannel")

    def featurize(self, ext_type: ExtendedType, channel: str) -> str:
        type_str = ext_type.value if hasattr(ext_type, "value") else str(ext_type)
        return f"{type_str}_{channel}"

    def _init_score(self) -> dict[str, float]:
        SCORE: dict[str, float] = {}

        CONTINUOUS_CHANNELS = {
            "x": 0.0, "y": 0.0, "size": -0.575, "color": -0.725,
            "text": -2.0, "opacity": -3.0,
            "shape": TERRIBLE, "row": TERRIBLE, "column": TERRIBLE,
            "detail": 2 * TERRIBLE,
        }

        for t in [Q, T, TIMEUNIT_T]:
            for channel, score in CONTINUOUS_CHANNELS.items():
                SCORE[self.featurize(t, channel)] = score

        ORDERED_CHANNELS = dict(CONTINUOUS_CHANNELS)
        ORDERED_CHANNELS.update({
            "row": -0.75, "column": -0.75,
            "shape": -3.1, "text": -3.2, "detail": -4.0,
        })

        for t in [BIN_Q, TIMEUNIT_O, O]:
            for channel, score in ORDERED_CHANNELS.items():
                SCORE[self.featurize(t, channel)] = score

        NOMINAL_CHANNELS = {
            "x": 0.0, "y": 0.0, "color": -0.6, "shape": -0.65,
            "row": -0.7, "column": -0.7, "text": -0.8,
            "detail": -2.0, "size": -3.0, "opacity": -3.1,
        }

        for channel, score in NOMINAL_CHANNELS.items():
            SCORE[self.featurize(N, channel)] = score
            # Key: position/detail not terrible, others penalized more
            if channel in ("x", "y", "detail"):
                SCORE[self.featurize(K, channel)] = -1.0
            else:
                SCORE[self.featurize(K, channel)] = score - 2.0

        return SCORE

    def get_score(self, spec_m, schema, opt) -> list[dict]:
        encoding_by_field: dict[str, list] = {}
        for enc_q in spec_m.get_encodings():
            auto_count = _fq_attr(enc_q, "autoCount")
            field = _fq_attr(enc_q, "field")
            if field is not None or auto_count:
                key = _field_def_shorthand(enc_q)
                encoding_by_field.setdefault(key, []).append(enc_q)

        features = []
        for enc_qs in encoding_by_field.values():
            best: dict | None = None
            for enc_q in enc_qs:
                auto_count = _fq_attr(enc_q, "autoCount")
                field = _fq_attr(enc_q, "field")
                if field is not None or auto_count:
                    ext_type = get_extended_type(enc_q)
                    channel = _fq_attr(enc_q, "channel")
                    channel_str = channel.value if hasattr(channel, "value") else str(channel) if channel else ""
                    feature = self.featurize(ext_type, channel_str)
                    fs = self._get_feature_score(feature)
                    if fs is not None and (best is None or fs["score"] > best["score"]):
                        best = fs
            if best is not None:
                features.append(best)
        return features
