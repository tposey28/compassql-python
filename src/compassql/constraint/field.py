from __future__ import annotations

from compassql.constraint.base import AbstractConstraint, EncodingConstraintModel
from compassql.propindex import PropIndex
from compassql.property import Property, get_encoding_nested_prop, SCALE_PROPS
from compassql.vegalite_types import VLType, Channel
from compassql.wildcard import is_wildcard


def _make(name_, description, properties, allow_wildcard, strict_, checker):
    c = AbstractConstraint(
        name_=name_,
        description=description,
        properties=properties,
        allow_wildcard_for_properties=allow_wildcard,
        strict_=strict_,
    )
    return EncodingConstraintModel(c, checker)


def _fq_attr(fq, attr, default=None):
    return getattr(fq, attr, default)


# --- Helper checker functions ---

def _channel_field_compatible(fq, schema, wc, opt):
    channel = _fq_attr(fq, "channel")
    ftype = _fq_attr(fq, "type")
    bin_ = _fq_attr(fq, "bin")
    time_unit = _fq_attr(fq, "timeUnit")

    if channel is None or ftype is None:
        return True

    channel_str = channel.value if hasattr(channel, "value") else str(channel)
    type_str = ftype.value if hasattr(ftype, "value") else str(ftype)

    if channel_str in ("row", "column", "facet"):
        if type_str in ("ordinal", "nominal"):
            return True
        if type_str == "temporal" and time_unit:
            return True
        if type_str == "quantitative" and not bin_:
            return False
        return True

    if channel_str in ("x2", "y2"):
        if type_str in ("ordinal", "nominal"):
            return False

    if channel_str == "size":
        if type_str == "nominal":
            return False

    return True


def _only_one_type_of_function(fq, schema, wc, opt):
    aggregate = _fq_attr(fq, "aggregate")
    bin_ = _fq_attr(fq, "bin")
    time_unit = _fq_attr(fq, "timeUnit")

    num_fn = (
        (1 if (not is_wildcard(aggregate) and aggregate) else 0) +
        (1 if (not is_wildcard(bin_) and bin_) else 0) +
        (1 if (not is_wildcard(time_unit) and time_unit) else 0)
    )
    return num_fn <= 1


def _time_unit_should_have_variation(fq, schema, wc, opt):
    time_unit = _fq_attr(fq, "timeUnit")
    ftype = _fq_attr(fq, "type")
    type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None

    if time_unit and type_str == "temporal":
        if not wc.has("timeUnit") and not getattr(opt, "constraint_manually_specified_value", False):
            return True
        return schema.time_unit_has_variation(fq)
    return True


def _scale_properties_supported_by_scale_type(fq, schema, wc, opt):
    scale = _fq_attr(fq, "scale")
    if not scale:
        return True
    try:
        from compassql.query.encoding import scale_type as get_scale_type
        s_type = get_scale_type(fq)
    except Exception:
        return True
    if s_type is None:
        return True
    return True


def _scale_properties_supported_by_channel(fq, schema, wc, opt):
    channel = _fq_attr(fq, "channel")
    scale = _fq_attr(fq, "scale")

    if not channel or is_wildcard(channel) or not scale:
        return True

    channel_str = channel.value if hasattr(channel, "value") else str(channel)
    if channel_str in ("row", "column", "facet"):
        return False
    return True


def _type_matches_primitive_type(fq, schema, wc, opt):
    field = _fq_attr(fq, "field")
    ftype = _fq_attr(fq, "type")

    if field == "*":
        return True

    if (not wc.has("field") and not wc.has("type") and
            not getattr(opt, "constraint_manually_specified_value", False)):
        return True

    primitive = schema.primitive_type(field)
    type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None

    if primitive is None:
        return False

    primitive_str = primitive.value if hasattr(primitive, "value") else str(primitive)

    if primitive_str in ("boolean", "string"):
        return type_str not in ("quantitative", "temporal")
    elif primitive_str in ("number", "integer"):
        return type_str != "temporal"
    elif primitive_str == "date":
        return type_str == "temporal"
    return True


def _type_matches_schema_type(fq, schema, wc, opt):
    field = _fq_attr(fq, "field")
    ftype = _fq_attr(fq, "type")

    if (not wc.has("field") and not wc.has("type") and
            not getattr(opt, "constraint_manually_specified_value", False)):
        return True

    if field == "*":
        return ftype in (VLType.QUANTITATIVE, "quantitative")

    schema_type = schema.vl_type(field)
    type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None
    schema_str = schema_type.value if hasattr(schema_type, "value") else str(schema_type) if schema_type else None
    return schema_str == type_str


def _data_type_and_function_match_scale_type(fq, schema, wc, opt):
    scale = _fq_attr(fq, "scale")
    if not scale:
        return True

    ftype = _fq_attr(fq, "type")
    bin_ = _fq_attr(fq, "bin")
    time_unit = _fq_attr(fq, "timeUnit")
    type_str = ftype.value if hasattr(ftype, "value") else str(ftype) if ftype else None

    scale_dict = scale if isinstance(scale, dict) else None
    s_type_str = scale_dict.get("type") if scale_dict else None

    discrete_types = {"ordinal", "nominal", "key"}
    discrete_scales = {"ordinal", "band", "point", "bin-ordinal"}
    continuous_q_scales = {"log", "pow", "sqrt", "quantile", "quantize", "linear"}

    if type_str in discrete_types:
        return s_type_str is None or s_type_str in discrete_scales
    elif type_str == "temporal":
        if not time_unit:
            return s_type_str in (None, "time", "utc")
        else:
            return s_type_str in (None, "time", "utc") or s_type_str in discrete_scales
    elif type_str == "quantitative":
        if bin_:
            return s_type_str in (None, "linear")
        else:
            return s_type_str is None or s_type_str in continuous_q_scales
    return True


# --- Constraint list (helpers defined above) ---

FIELD_CONSTRAINTS: list[EncodingConstraintModel] = [

    _make(
        "aggregateOpSupportedByType",
        "Aggregate function should be supported by data type.",
        [Property.TYPE, Property.AGGREGATE],
        False, True,
        lambda fq, schema, wc, opt: (
            True if not _fq_attr(fq, "aggregate")
            else _fq_attr(fq, "type") not in (VLType.ORDINAL, VLType.NOMINAL, "ordinal", "nominal", "key")
        ),
    ),

    _make(
        "asteriskFieldWithCountOnly",
        'Field="*" should be disallowed except aggregate="count"',
        [Property.FIELD, Property.AGGREGATE],
        False, True,
        lambda fq, schema, wc, opt: (
            (_fq_attr(fq, "field") == "*") == (_fq_attr(fq, "aggregate") == "count")
        ),
    ),

    _make(
        "minCardinalityForBin",
        "binned quantitative field should not have too low cardinality",
        [Property.BIN, Property.FIELD, Property.TYPE],
        False, True,
        lambda fq, schema, wc, opt: (
            schema.cardinality({
                "channel": _fq_attr(fq, "channel"),
                "field": _fq_attr(fq, "field"),
                "type": _fq_attr(fq, "type"),
            }) >= opt.min_cardinality_for_bin
            if (_fq_attr(fq, "bin") and _fq_attr(fq, "type") in (VLType.QUANTITATIVE, "quantitative"))
            else True
        ),
    ),

    _make(
        "binAppliedForQuantitative",
        "bin should be applied to quantitative field only.",
        [Property.TYPE, Property.BIN],
        False, True,
        lambda fq, schema, wc, opt: (
            _fq_attr(fq, "type") in (VLType.QUANTITATIVE, "quantitative")
            if _fq_attr(fq, "bin") else True
        ),
    ),

    _make(
        "channelFieldCompatible",
        "encoding channel's range type be compatible with channel type.",
        [Property.CHANNEL, Property.TYPE, Property.BIN, Property.TIMEUNIT],
        False, True,
        _channel_field_compatible,
    ),

    _make(
        "hasFn",
        "A field with hasFn flag should have one of aggregate, timeUnit, or bin.",
        [Property.AGGREGATE, Property.BIN, Property.TIMEUNIT],
        True, True,
        lambda fq, schema, wc, opt: (
            (bool(_fq_attr(fq, "aggregate")) or bool(_fq_attr(fq, "bin")) or bool(_fq_attr(fq, "timeUnit")))
            if _fq_attr(fq, "hasFn") else True
        ),
    ),

    _make(
        "omitScaleZeroWithBinnedField",
        "Do not use scale zero with binned field",
        [Property.SCALE, get_encoding_nested_prop("scale", "zero"), Property.BIN],
        False, True,
        lambda fq, schema, wc, opt: (
            not ((_fq_attr(fq, "scale") or {}).get("zero") is True)
            if _fq_attr(fq, "bin") and _fq_attr(fq, "scale") else True
        ),
    ),

    _make(
        "onlyOneTypeOfFunction",
        "Only one of aggregate, autoCount, timeUnit, or bin should be applied at the same time.",
        [Property.AGGREGATE, Property.AUTOCOUNT, Property.TIMEUNIT, Property.BIN],
        True, True,
        _only_one_type_of_function,
    ),

    _make(
        "timeUnitAppliedForTemporal",
        "Time unit should be applied to temporal field only.",
        [Property.TYPE, Property.TIMEUNIT],
        False, True,
        lambda fq, schema, wc, opt: (
            False if (_fq_attr(fq, "timeUnit") and _fq_attr(fq, "type") not in (VLType.TEMPORAL, "temporal"))
            else True
        ),
    ),

    _make(
        "timeUnitShouldHaveVariation",
        "A particular time unit should be applied only if they produce unique values.",
        [Property.TIMEUNIT, Property.TYPE],
        False, False,
        _time_unit_should_have_variation,
    ),

    _make(
        "scalePropertiesSupportedByScaleType",
        "Scale properties must be supported by correct scale type",
        list(SCALE_PROPS) + [Property.SCALE, Property.TYPE],
        True, True,
        _scale_properties_supported_by_scale_type,
    ),

    _make(
        "scalePropertiesSupportedByChannel",
        "Not all scale properties are supported by all encoding channels",
        list(SCALE_PROPS) + [Property.SCALE, Property.CHANNEL],
        True, True,
        _scale_properties_supported_by_channel,
    ),

    _make(
        "typeMatchesPrimitiveType",
        "Data type should be supported by field's primitive type.",
        [Property.FIELD, Property.TYPE],
        False, True,
        _type_matches_primitive_type,
    ),

    _make(
        "typeMatchesSchemaType",
        "Enumerated data type of a field should match the field's type in the schema.",
        [Property.FIELD, Property.TYPE],
        False, False,
        _type_matches_schema_type,
    ),

    _make(
        "maxCardinalityForCategoricalColor",
        "Categorical channel should not have too high cardinality",
        [Property.CHANNEL, Property.FIELD],
        False, False,
        lambda fq, schema, wc, opt: (
            schema.cardinality(vars(fq)) <= opt.max_cardinality_for_categorical_color
            if (_fq_attr(fq, "channel") in (Channel.COLOR, "color") and
                _fq_attr(fq, "type") in (VLType.NOMINAL, "nominal", "key"))
            else True
        ),
    ),

    _make(
        "maxCardinalityForFacet",
        "Row/column channel should not have too high cardinality",
        [Property.CHANNEL, Property.FIELD, Property.BIN, Property.TIMEUNIT],
        False, False,
        lambda fq, schema, wc, opt: (
            schema.cardinality(vars(fq)) <= opt.max_cardinality_for_facet
            if _fq_attr(fq, "channel") in (Channel.ROW, Channel.COLUMN, "row", "column")
            else True
        ),
    ),

    _make(
        "maxCardinalityForShape",
        "Shape channel should not have too high cardinality",
        [Property.CHANNEL, Property.FIELD, Property.BIN, Property.TIMEUNIT],
        False, False,
        lambda fq, schema, wc, opt: (
            schema.cardinality(vars(fq)) <= opt.max_cardinality_for_shape
            if _fq_attr(fq, "channel") in (Channel.SHAPE, "shape")
            else True
        ),
    ),

    _make(
        "dataTypeAndFunctionMatchScaleType",
        "Scale type must match data type",
        [
            Property.TYPE,
            Property.SCALE,
            get_encoding_nested_prop("scale", "type"),
            Property.TIMEUNIT,
            Property.BIN,
        ],
        False, True,
        _data_type_and_function_match_scale_type,
    ),

    _make(
        "stackIsOnlyUsedWithXY",
        "stack should only be allowed for x and y channels",
        [Property.STACK, Property.CHANNEL],
        False, True,
        lambda fq, schema, wc, opt: (
            _fq_attr(fq, "channel") in (Channel.X, Channel.Y, "x", "y")
            if _fq_attr(fq, "stack") else True
        ),
    ),
]


FIELD_CONSTRAINT_INDEX: dict[str, EncodingConstraintModel] = {
    c.name(): c for c in FIELD_CONSTRAINTS
}

FIELD_CONSTRAINTS_BY_PROPERTY: PropIndex = PropIndex()
for _c in FIELD_CONSTRAINTS:
    for _prop in _c._c.properties:
        _existing = FIELD_CONSTRAINTS_BY_PROPERTY.get(_prop) or []
        FIELD_CONSTRAINTS_BY_PROPERTY.set(_prop, _existing + [_c])
