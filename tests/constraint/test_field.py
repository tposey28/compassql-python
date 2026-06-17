"""Port of test/constraint/field.test.ts"""
from __future__ import annotations

import pytest

from compassql.config import DEFAULT_QUERY_CONFIG
from compassql.constraint.base import EncodingConstraintModel, AbstractConstraint
from compassql.constraint.field import FIELD_CONSTRAINTS, FIELD_CONSTRAINT_INDEX
from compassql.propindex import PropIndex
from compassql.property import Property, get_encoding_nested_prop
from compassql.wildcard import SHORT_WILDCARD
from tests.fixture import schema

default_opt = DEFAULT_QUERY_CONFIG
CONSTRAINT_MANUALLY_SPECIFIED_CONFIG = DEFAULT_QUERY_CONFIG.__class__(
    **{
        **{f: getattr(DEFAULT_QUERY_CONFIG, f) for f in DEFAULT_QUERY_CONFIG.__dataclass_fields__},
        "constraint_manually_specified_value": True,
    }
)


# All non-strict constraints must have a corresponding config key
def test_non_strict_constraints_have_config():
    for constraint in FIELD_CONSTRAINTS:
        if not constraint.strict():
            name = constraint.name()
            # Convert camelCase constraint name to snake_case config attr
            import re
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            assert hasattr(DEFAULT_QUERY_CONFIG, snake), (
                f"{name} should have default config but {snake} not found on QueryConfig"
            )


class TestHasAllRequiredPropertiesSpecific:
    enc_model = EncodingConstraintModel(
        AbstractConstraint(
            name_="TestEncoding",
            description="test",
            properties=[
                Property.AGGREGATE,
                Property.TYPE,
                Property.SCALE,
                get_encoding_nested_prop("scale", "type"),
            ],
            allow_wildcard_for_properties=False,
            strict_=True,
        ),
        checker=lambda *args: True,
    )

    def test_returns_true_if_all_properties_defined(self):
        enc_q = {"channel": "x", "aggregate": "mean", "field": "A", "scale": {"type": "log"}, "type": "quantitative"}
        assert self.enc_model.has_all_required_properties_specific(enc_q)

    def test_returns_true_if_required_property_undefined(self):
        enc_q = {"channel": "x", "field": "A", "scale": {"type": "log"}, "type": "quantitative"}
        assert self.enc_model.has_all_required_properties_specific(enc_q)

    def test_returns_false_if_required_property_is_wildcard(self):
        enc_q = {"channel": "x", "aggregate": SHORT_WILDCARD, "scale": {"type": "log"}, "type": "quantitative"}
        assert not self.enc_model.has_all_required_properties_specific(enc_q)

    def test_returns_false_if_nested_required_property_is_wildcard(self):
        enc_q = {"channel": "x", "aggregate": "mean", "field": "A", "scale": {"type": SHORT_WILDCARD}, "type": "quantitative"}
        assert not self.enc_model.has_all_required_properties_specific(enc_q)


class TestAggregateOpSupportedByType:
    def test_false_for_aggregate_on_nominal_or_ordinal(self):
        for vl_type in ("nominal", "ordinal"):
            enc_q = {"channel": "x", "aggregate": "mean", "field": "A", "type": vl_type}
            assert not FIELD_CONSTRAINT_INDEX["aggregateOpSupportedByType"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )

    def test_true_for_aggregate_on_quantitative_or_temporal(self):
        for vl_type in ("quantitative", "temporal"):
            enc_q = {"channel": "x", "aggregate": "mean", "field": "A", "type": vl_type}
            assert FIELD_CONSTRAINT_INDEX["aggregateOpSupportedByType"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )


class TestAsteriskFieldWithCountOnly:
    def test_true_for_count_on_asterisk(self):
        assert FIELD_CONSTRAINT_INDEX["asteriskFieldWithCountOnly"].satisfy(
            {"channel": "x", "aggregate": "count", "field": "*", "type": "quantitative"},
            schema, PropIndex(), default_opt
        )

    def test_false_for_asterisk_without_count(self):
        assert not FIELD_CONSTRAINT_INDEX["asteriskFieldWithCountOnly"].satisfy(
            {"channel": "x", "field": "*", "type": "quantitative"},
            schema, PropIndex(), default_opt
        )

    def test_false_for_count_without_asterisk(self):
        assert not FIELD_CONSTRAINT_INDEX["asteriskFieldWithCountOnly"].satisfy(
            {"channel": "x", "aggregate": "count", "field": "haha", "type": "quantitative"},
            schema, PropIndex(), default_opt
        )


class TestMinCardinalityForBin:
    def test_false_for_low_cardinality_fields(self):
        for field_name in ("Q5", "Q10"):
            enc_q = {"channel": "x", "bin": True, "field": field_name, "type": "quantitative"}
            assert not FIELD_CONSTRAINT_INDEX["minCardinalityForBin"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )

    def test_true_for_high_cardinality_fields(self):
        for field_name in ("Q15", "Q20", "Q"):
            enc_q = {"channel": "x", "bin": True, "field": field_name, "type": "quantitative"}
            assert FIELD_CONSTRAINT_INDEX["minCardinalityForBin"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )


class TestBinAppliedForQuantitative:
    def test_false_for_bin_on_non_quantitative(self):
        for vl_type in ("nominal", "ordinal", "temporal"):
            enc_q = {"channel": "x", "bin": True, "field": "A", "type": vl_type}
            assert not FIELD_CONSTRAINT_INDEX["binAppliedForQuantitative"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )

    def test_true_for_bin_on_quantitative(self):
        enc_q = {"channel": "x", "bin": True, "field": "A", "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["binAppliedForQuantitative"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )

    def test_true_for_non_binned_field(self):
        for vl_type in ("nominal", "ordinal", "temporal", "quantitative"):
            enc_q = {"channel": "x", "field": "A", "type": vl_type}
            assert FIELD_CONSTRAINT_INDEX["binAppliedForQuantitative"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )


class TestChannelFieldCompatible:
    positional_channels = ["x", "y", "color", "text", "detail"]

    def test_positional_channels_support_raw_measure(self):
        for ch in self.positional_channels:
            enc_q = {"channel": ch, "field": "Q", "type": "quantitative"}
            assert FIELD_CONSTRAINT_INDEX["channelFieldCompatible"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_positional_channels_support_aggregate_measure(self):
        for ch in self.positional_channels:
            enc_q = {"channel": ch, "field": "Q", "type": "quantitative", "aggregate": "mean"}
            assert FIELD_CONSTRAINT_INDEX["channelFieldCompatible"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_positional_channels_support_ordinal(self):
        for ch in self.positional_channels:
            enc_q = {"channel": ch, "field": "O", "type": "ordinal"}
            assert FIELD_CONSTRAINT_INDEX["channelFieldCompatible"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_row_column_do_not_support_raw_measure(self):
        for ch in ("row", "column"):
            enc_q = {"channel": ch, "field": "Q", "type": "quantitative"}
            assert not FIELD_CONSTRAINT_INDEX["channelFieldCompatible"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_row_column_do_not_support_aggregate_measure(self):
        for ch in ("row", "column"):
            enc_q = {"channel": ch, "field": "Q", "type": "quantitative", "aggregate": "mean"}
            assert not FIELD_CONSTRAINT_INDEX["channelFieldCompatible"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_row_column_support_timeunit_temporal(self):
        for ch in ("row", "column"):
            for vl_type in ("ordinal", "temporal"):
                enc_q = {"channel": ch, "field": "T", "type": vl_type, "timeUnit": "month"}
                assert FIELD_CONSTRAINT_INDEX["channelFieldCompatible"].satisfy(
                    enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
                )

    def test_size_does_not_support_nominal(self):
        enc_q = {"channel": "size", "field": "N", "type": "nominal"}
        assert not FIELD_CONSTRAINT_INDEX["channelFieldCompatible"].satisfy(
            enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
        )


class TestHasFn:
    def test_true_if_no_hasfn(self):
        enc_q = {"channel": "color", "field": "Q", "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["hasFn"].satisfy(enc_q, schema, PropIndex(), default_opt)

    def test_false_if_hasfn_true_with_no_function(self):
        enc_q = {"hasFn": True, "channel": "color", "field": "Q", "type": "quantitative"}
        assert not FIELD_CONSTRAINT_INDEX["hasFn"].satisfy(enc_q, schema, PropIndex(), default_opt)

    def test_true_if_hasfn_true_with_aggregate(self):
        enc_q = {"hasFn": True, "channel": "color", "aggregate": "mean", "field": "Q", "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["hasFn"].satisfy(enc_q, schema, PropIndex(), default_opt)

    def test_true_if_hasfn_true_with_bin(self):
        enc_q = {"hasFn": True, "channel": "color", "bin": True, "field": "Q", "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["hasFn"].satisfy(enc_q, schema, PropIndex(), default_opt)

    def test_true_if_hasfn_true_with_timeunit(self):
        enc_q = {"hasFn": True, "channel": "color", "timeUnit": "hours", "field": "T", "type": "temporal"}
        assert FIELD_CONSTRAINT_INDEX["hasFn"].satisfy(enc_q, schema, PropIndex(), default_opt)


class TestMaxCardinalityForCategoricalColor:
    def test_true_for_low_cardinality(self):
        for field_name in ("O", "O_10", "O_20"):
            enc_q = {"channel": "color", "field": field_name, "type": "nominal"}
            assert FIELD_CONSTRAINT_INDEX["maxCardinalityForCategoricalColor"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )

    def test_false_for_high_cardinality(self):
        enc_q = {"channel": "color", "field": "O_100", "type": "nominal"}
        assert not FIELD_CONSTRAINT_INDEX["maxCardinalityForCategoricalColor"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )


class TestMaxCardinalityForFacet:
    def test_true_for_low_cardinality(self):
        for ch in ("row", "column"):
            for field_name in ("O", "O_10"):
                enc_q = {"channel": ch, "field": field_name, "type": "nominal"}
                assert FIELD_CONSTRAINT_INDEX["maxCardinalityForFacet"].satisfy(
                    enc_q, schema, PropIndex(), default_opt
                )

    def test_false_for_high_cardinality(self):
        for ch in ("row", "column"):
            enc_q = {"channel": ch, "field": "O_100", "type": "nominal"}
            assert not FIELD_CONSTRAINT_INDEX["maxCardinalityForFacet"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )


class TestMaxCardinalityForShape:
    def test_true_for_low_cardinality(self):
        enc_q = {"channel": "shape", "field": "O", "type": "nominal"}
        assert FIELD_CONSTRAINT_INDEX["maxCardinalityForShape"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )

    def test_false_for_high_cardinality(self):
        for field_name in ("O_10", "O_20", "O_100"):
            enc_q = {"channel": "shape", "field": field_name, "type": "nominal"}
            assert not FIELD_CONSTRAINT_INDEX["maxCardinalityForShape"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )


class TestOmitBinWithLogScale:
    def test_bin_does_not_support_log_scale(self):
        enc_q = {"channel": "x", "field": "Q", "bin": True, "scale": {"type": "log"}, "type": "quantitative"}
        assert not FIELD_CONSTRAINT_INDEX["dataTypeAndFunctionMatchScaleType"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )


class TestOmitScaleZeroWithBinnedField:
    def test_false_if_scale_zero_with_binned_field(self):
        enc_q = {"channel": "x", "bin": True, "field": "A", "scale": {"zero": True}, "type": "quantitative"}
        assert not FIELD_CONSTRAINT_INDEX["omitScaleZeroWithBinnedField"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )

    def test_true_if_no_scale_zero_with_binned_field(self):
        enc_q = {"channel": "x", "bin": True, "field": "A", "scale": {"zero": False}, "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["omitScaleZeroWithBinnedField"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )


class TestDataTypeAndFunctionMatchScaleType:
    @pytest.mark.parametrize("scale_type", ["ordinal", "point", "band"])
    def test_discrete_scale_matches_ordinal_with_timeunit(self, scale_type):
        enc_q = {"channel": "x", "field": "O", "scale": {"type": scale_type}, "type": "ordinal", "timeUnit": "minutes"}
        assert FIELD_CONSTRAINT_INDEX["dataTypeAndFunctionMatchScaleType"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )

    @pytest.mark.parametrize("scale_type", ["ordinal", "point", "band"])
    def test_discrete_scale_matches_nominal(self, scale_type):
        enc_q = {"channel": "x", "field": "N", "scale": {"type": scale_type}, "type": "nominal", "timeUnit": "minutes"}
        assert FIELD_CONSTRAINT_INDEX["dataTypeAndFunctionMatchScaleType"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )

    @pytest.mark.parametrize("scale_type", ["time", "utc", "ordinal", "point", "band"])
    def test_temporal_scale_matches_temporal(self, scale_type):
        enc_q = {"channel": "x", "field": "T", "scale": {"type": scale_type}, "type": "temporal", "timeUnit": "minutes"}
        assert FIELD_CONSTRAINT_INDEX["dataTypeAndFunctionMatchScaleType"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )

    @pytest.mark.parametrize("scale_type", ["log", "pow", "sqrt", "linear"])
    def test_quantitative_scale_matches_quantitative(self, scale_type):
        enc_q = {"channel": "x", "field": "Q", "scale": {"type": scale_type}, "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["dataTypeAndFunctionMatchScaleType"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )


class TestOnlyOneTypeOfFunction:
    def test_true_if_no_function(self):
        enc_q = {"channel": "x", "field": "A", "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["onlyOneTypeOfFunction"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )

    def test_false_if_multiple_functions(self):
        combos = [
            ("mean", "month", True),
            ("mean", None, True),
            ("mean", "month", None),
            (None, "month", True),
        ]
        for agg, tu, bin_val in combos:
            enc_q = {"channel": "x", "field": "A", "type": "quantitative"}
            if agg is not None:
                enc_q["aggregate"] = agg
            if tu is not None:
                enc_q["timeUnit"] = tu
            if bin_val is not None:
                enc_q["bin"] = bin_val
            assert not FIELD_CONSTRAINT_INDEX["onlyOneTypeOfFunction"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )


class TestTimeUnitAppliedForTemporal:
    def test_false_for_timeunit_on_non_temporal(self):
        for vl_type in ("nominal", "ordinal", "quantitative"):
            enc_q = {"channel": "x", "timeUnit": "month", "field": "A", "type": vl_type}
            assert not FIELD_CONSTRAINT_INDEX["timeUnitAppliedForTemporal"].satisfy(
                enc_q, schema, PropIndex(), default_opt
            )

    def test_true_for_timeunit_on_temporal(self):
        enc_q = {"channel": "x", "timeUnit": "month", "field": "A", "type": "temporal"}
        assert FIELD_CONSTRAINT_INDEX["timeUnitAppliedForTemporal"].satisfy(
            enc_q, schema, PropIndex(), default_opt
        )


class TestTypeMatchesSchemaType:
    def test_false_if_type_does_not_match_schema_type(self):
        for vl_type in ("temporal", "quantitative", "nominal"):
            enc_q = {"channel": "x", "field": "O", "type": vl_type}
            assert not FIELD_CONSTRAINT_INDEX["typeMatchesSchemaType"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_true_if_type_matches_schema_type(self):
        enc_q = {"channel": "x", "field": "O", "type": "ordinal"}
        assert FIELD_CONSTRAINT_INDEX["typeMatchesSchemaType"].satisfy(
            enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
        )

    def test_false_if_field_does_not_exist(self):
        enc_q = {"channel": "x", "field": "random", "type": "nominal"}
        assert not FIELD_CONSTRAINT_INDEX["typeMatchesSchemaType"].satisfy(
            enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
        )

    def test_false_if_asterisk_field_non_quantitative(self):
        for vl_type in ("temporal", "ordinal", "nominal"):
            enc_q = {"channel": "x", "aggregate": "count", "field": "*", "type": vl_type}
            assert not FIELD_CONSTRAINT_INDEX["typeMatchesSchemaType"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_true_if_asterisk_field_quantitative(self):
        enc_q = {"channel": "x", "aggregate": "count", "field": "*", "type": "quantitative"}
        assert FIELD_CONSTRAINT_INDEX["typeMatchesSchemaType"].satisfy(
            enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
        )


class TestTypeMatchesPrimitiveType:
    def test_false_if_string_used_as_quantitative_or_temporal(self):
        for vl_type in ("temporal", "quantitative"):
            enc_q = {"channel": "x", "field": "O", "type": vl_type}
            assert not FIELD_CONSTRAINT_INDEX["typeMatchesPrimitiveType"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_true_if_string_used_as_ordinal_or_nominal(self):
        for vl_type in ("nominal", "ordinal"):
            enc_q = {"channel": "x", "field": "O", "type": vl_type}
            assert FIELD_CONSTRAINT_INDEX["typeMatchesPrimitiveType"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_false_if_field_does_not_exist(self):
        enc_q = {"channel": "x", "field": "random", "type": "nominal"}
        assert not FIELD_CONSTRAINT_INDEX["typeMatchesPrimitiveType"].satisfy(
            enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
        )

    def test_true_if_asterisk_field_any_type(self):
        for vl_type in ("temporal", "ordinal", "nominal", "quantitative"):
            enc_q = {"channel": "x", "aggregate": "count", "field": "*", "type": vl_type}
            assert FIELD_CONSTRAINT_INDEX["typeMatchesPrimitiveType"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )


class TestStackIsOnlyUsedWithXY:
    def test_true_for_stack_in_x_or_y(self):
        for ch in ("x", "y"):
            enc_q = {"channel": ch, "stack": "zero"}
            assert FIELD_CONSTRAINT_INDEX["stackIsOnlyUsedWithXY"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )

    def test_false_for_stack_in_non_xy_channel(self):
        non_xy = ["row", "column", "color", "size", "shape", "detail", "text", "tooltip"]
        for ch in non_xy:
            enc_q = {"channel": ch, "stack": "zero"}
            assert not FIELD_CONSTRAINT_INDEX["stackIsOnlyUsedWithXY"].satisfy(
                enc_q, schema, PropIndex(), CONSTRAINT_MANUALLY_SPECIFIED_CONFIG
            )
