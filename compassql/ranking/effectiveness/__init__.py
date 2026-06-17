from __future__ import annotations

from compassql.ranking.effectiveness.axis import AxisScorer
from compassql.ranking.effectiveness.dimension import DimensionScorer
from compassql.ranking.effectiveness.facet import FacetScorer
from compassql.ranking.effectiveness.mark import MarkScorer
from compassql.ranking.effectiveness.sizechannel import SizeChannelScorer
from compassql.ranking.effectiveness.typechannel import TypeChannelScorer

_SCORERS = [
    AxisScorer(),
    DimensionScorer(),
    FacetScorer(),
    MarkScorer(),
    SizeChannelScorer(),
    TypeChannelScorer(),
]


def effectiveness(spec_m, schema, opt) -> dict:
    features = []
    for scorer in _SCORERS:
        features.extend(scorer.get_score(spec_m, schema, opt))

    return {
        "score": sum(f["score"] for f in features),
        "features": features,
    }
