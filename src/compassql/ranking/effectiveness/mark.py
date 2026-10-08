from __future__ import annotations

from compassql.ranking.effectiveness.base import Scorer
from compassql.ranking.effectiveness.type import ExtendedType, Q, T, BIN_Q, TIMEUNIT_T, TIMEUNIT_O, O, N, K, NONE, get_extended_type


def _fq_attr(fq, attr, default=None):
    return getattr(fq, attr, default)


def featurize(x_type: ExtendedType, y_type: ExtendedType, has_occlusion: bool, mark: str) -> str:
    x = x_type.value if hasattr(x_type, "value") else str(x_type)
    y = y_type.value if hasattr(y_type, "value") else str(y_type)
    return f"{x}_{y}_{has_occlusion}_{mark}"


def _build_score_index() -> dict[str, float]:
    SCORE: dict[str, float] = {}

    MEASURES = [Q, T]
    DISCRETE = [BIN_Q, TIMEUNIT_O, O, N, K]
    DISCRETE_OR_NONE = DISCRETE + [NONE]

    # QxQ
    for x_type in MEASURES:
        for y_type in MEASURES:
            occluded_qq = {
                "point": 0, "text": -0.2, "tick": -0.5,
                "rect": -1, "bar": -2, "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in occluded_qq.items():
                SCORE[featurize(x_type, y_type, True, mark)] = score

            no_occluded_qq = {
                "point": 0, "text": -0.2, "tick": -0.5,
                "bar": -2, "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in no_occluded_qq.items():
                SCORE[featurize(x_type, y_type, False, mark)] = score

    # DxQ, QxD
    for x_type in MEASURES:
        # Has occlusion — DISCRETE_OR_NONE
        for y_type in DISCRETE_OR_NONE:
            occluded_dm = {
                "tick": 0, "point": -0.2, "text": -0.5,
                "bar": -2, "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in occluded_dm.items():
                SCORE[featurize(x_type, y_type, True, mark)] = score
                SCORE[featurize(y_type, x_type, True, mark)] = score

        # Has occlusion — TIMEUNIT_T
        for y_type in [TIMEUNIT_T]:
            occluded_tu = {
                "point": 0, "text": -0.5, "tick": -1,
                "bar": -2, "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in occluded_tu.items():
                SCORE[featurize(x_type, y_type, True, mark)] = score
                SCORE[featurize(y_type, x_type, True, mark)] = score

        # No occlusion — NONE, N, O, K
        for y_type in [NONE, N, O, K]:
            no_occ_qxn = {
                "bar": 0, "point": -0.2, "tick": -0.25, "text": -0.3,
                "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in no_occ_qxn.items():
                SCORE[featurize(x_type, y_type, False, mark)] = score
                SCORE[featurize(y_type, x_type, False, mark)] = score

        # No occlusion — BIN_Q
        for y_type in [BIN_Q]:
            no_occ_qxbinq = {
                "bar": 0, "point": -0.2, "tick": -0.25, "text": -0.3,
                "line": -0.5, "area": -0.5, "rule": -2.5,
            }
            for mark, score in no_occ_qxbinq.items():
                SCORE[featurize(x_type, y_type, False, mark)] = score
                SCORE[featurize(y_type, x_type, False, mark)] = score

        # No occlusion — TIMEUNIT_T, TIMEUNIT_O
        for y_type in [TIMEUNIT_T, TIMEUNIT_O]:
            no_occ_qxtu = {
                "line": 0, "area": -0.1, "bar": -0.2, "point": -0.3,
                "tick": -0.35, "text": -0.4, "rule": -2.5,
            }
            for mark, score in no_occ_qxtu.items():
                SCORE[featurize(x_type, y_type, False, mark)] = score
                SCORE[featurize(y_type, x_type, False, mark)] = score

    # TIMEUNIT_T x TIMEUNIT_T
    for x_type in [TIMEUNIT_T]:
        for y_type in [TIMEUNIT_T]:
            tt_mark = {
                "point": 0, "rect": -0.1, "text": -0.5,
                "tick": -1, "bar": -2, "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in tt_mark.items():
                SCORE[featurize(x_type, y_type, True, mark)] = score
                SCORE[featurize(x_type, y_type, False, mark)] = score

        # TIMEUNIT_T x DISCRETE_OR_NONE
        for y_type in DISCRETE_OR_NONE:
            td_mark = {
                "tick": 0, "point": -0.2, "text": -0.5,
                "rect": -1, "bar": -2, "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in td_mark.items():
                SCORE[featurize(x_type, y_type, True, mark)] = score
                SCORE[featurize(y_type, x_type, True, mark)] = score
                SCORE[featurize(x_type, y_type, False, mark)] = score
                SCORE[featurize(y_type, x_type, False, mark)] = score

    # DxD
    for x_type in DISCRETE_OR_NONE:
        for y_type in DISCRETE_OR_NONE:
            dd_mark = {
                "point": 0, "rect": 0, "text": -0.1,
                "tick": -1, "bar": -2, "line": -2, "area": -2, "rule": -2.5,
            }
            for mark, score in dd_mark.items():
                SCORE[featurize(x_type, y_type, True, mark)] = score
                SCORE[featurize(x_type, y_type, False, mark)] = score

    return SCORE


class MarkScorer(Scorer):
    def __init__(self):
        super().__init__("Mark")

    def _init_score(self) -> dict[str, float]:
        return _build_score_index()

    def get_score(self, spec_m, schema, opt) -> list[dict]:
        mark = spec_m.get_mark()
        mark_str = mark.value if hasattr(mark, "value") else str(mark) if mark else ""
        # Treat circle/square as point
        if mark_str in ("circle", "square"):
            mark_str = "point"

        x_enc = spec_m.get_encoding_query_by_channel("x")
        x_type = get_extended_type(x_enc) if x_enc else NONE

        y_enc = spec_m.get_encoding_query_by_channel("y")
        y_type = get_extended_type(y_enc) if y_enc else NONE

        is_occluded = not spec_m.is_aggregate()

        feature = featurize(x_type, y_type, is_occluded, mark_str)
        fs = self._get_feature_score(feature)
        if fs:
            return [fs]
        return []
