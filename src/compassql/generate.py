from __future__ import annotations

from typing import Any

from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.enumerator import get_enumerator
from compassql.property import from_key
from compassql.query.spec import SpecQuery


def generate(spec_q: SpecQuery, schema: Any, opt: Any = None) -> list[Any]:
    from compassql.model import SpecQueryModel
    from compassql.stylize import stylize

    if opt is None:
        opt = DEFAULT_QUERY_CONFIG

    # Build SpecQueryModel (also builds wildcard_index)
    spec_m = SpecQueryModel.build(spec_q, schema, opt)
    wildcard_index = spec_m.wildcard_index

    # Start with the single input spec model
    answer_set: list[Any] = [spec_m]

    for prop_key in opt.property_precedence:
        prop = from_key(prop_key)
        if wildcard_index.has_property(prop):
            factory = get_enumerator(prop)
            if factory is None:
                continue
            enumerator = factory(wildcard_index, schema, opt)
            new_answer_set: list[Any] = []
            for candidate in answer_set:
                for result in enumerator(candidate):
                    new_answer_set.append(result)
            answer_set = new_answer_set

    if getattr(opt, "stylize", False):
        if (
            getattr(opt, "nominal_color_scale_for_high_cardinality", None) is not None
            or getattr(opt, "small_range_step_for_high_cardinality_or_facet", None) is not None
            or getattr(opt, "x_axis_on_top_for_high_y_cardinality_without_column", None) is not None
        ):
            return stylize(answer_set, schema, opt)

    return answer_set
