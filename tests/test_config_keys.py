"""Query config key handling in recommend().

Upstream CompassQL spells query config keys in camelCase; QueryConfig
fields are snake_case. Both spellings must reach the config object, and a
key matching neither must be reported rather than silently dropped.
"""
from __future__ import annotations

import warnings

import pytest

from tests.fixture import schema
from compassql.query.query import Query
from compassql.recommend import recommend
from compassql.schema import Schema

_SPEC = {
    "mark": "?",
    "encodings": [
        {"channel": "x", "field": "Q", "type": "quantitative"},
        {"channel": "y", "field": "Q1", "type": "quantitative"},
    ],
}


def _config_of(query_config=None, arg_config=None, data_schema=None, spec=None):
    """Run recommend() and return the QueryConfig it actually used."""
    d = {"spec": spec or _SPEC, "orderBy": "effectiveness"}
    if query_config is not None:
        d["config"] = query_config
    result = recommend(Query.from_dict(d), data_schema or schema, arg_config)
    return result["query"].config


def test_camel_case_key_sets_field():
    assert _config_of({"autoAddCount": True}).auto_add_count is True


def test_snake_case_key_still_works():
    assert _config_of({"auto_add_count": True}).auto_add_count is True


def test_camel_and_snake_case_are_equivalent():
    camel = _config_of({"omitBarLineAreaWithOcclusion": False})
    snake = _config_of({"omit_bar_line_area_with_occlusion": False})
    assert camel.omit_bar_line_area_with_occlusion is False
    assert snake.omit_bar_line_area_with_occlusion is False


@pytest.mark.parametrize(
    "config",
    [
        {"auto_add_count": True, "autoAddCount": False},
        {"autoAddCount": False, "auto_add_count": True},
    ],
    ids=["snake-first", "camel-first"],
)
def test_snake_case_wins_when_both_spellings_present(config):
    assert _config_of(config).auto_add_count is True


def test_unknown_key_warns_without_raising():
    with pytest.warns(UserWarning, match="notARealSetting"):
        _config_of({"notARealSetting": 3})


def test_unknown_key_does_not_reach_the_config_object():
    with pytest.warns(UserWarning):
        config = _config_of({"notARealSetting": 3})
    assert not hasattr(config, "notARealSetting")
    assert not hasattr(config, "not_a_real_setting")


def test_known_keys_alongside_an_unknown_one_still_apply():
    with pytest.warns(UserWarning, match="bogusKey"):
        config = _config_of({"bogusKey": 1, "autoAddCount": True})
    assert config.auto_add_count is True


def test_no_warning_for_recognized_keys():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        _config_of({"autoAddCount": True, "omit_raw": True})


def test_defaults_apply_when_nothing_is_supplied():
    config = _config_of()
    assert config.auto_add_count is False
    assert config.omit_bar_line_area_with_occlusion is True


def test_config_argument_beats_defaults():
    config = _config_of(arg_config={"autoAddCount": True})
    assert config.auto_add_count is True


def test_query_config_beats_config_argument():
    config = _config_of(
        query_config={"autoAddCount": False},
        arg_config={"autoAddCount": True},
    )
    assert config.auto_add_count is False


def test_query_config_beats_config_argument_across_spellings():
    """Precedence is by setting, not by spelling."""
    config = _config_of(
        query_config={"omit_bar_line_area_with_occlusion": False},
        arg_config={"omitBarLineAreaWithOcclusion": True},
    )
    assert config.omit_bar_line_area_with_occlusion is False


def _marks(config):
    """Marks in the answer set for a raw temporal-x / quantitative-y plot."""
    rows = [{"date": f"2024-01-{d:02d}", "value": float(d)} for d in range(1, 13)]
    spec = {
        "mark": "?",
        "encodings": [
            {"channel": "x", "field": "date", "type": "temporal"},
            {"channel": "y", "field": "value", "type": "quantitative"},
        ],
    }
    d = {"spec": spec, "orderBy": "effectiveness"}
    if config is not None:
        d["config"] = config
    result = recommend(Query.from_dict(d), Schema.build_from_data(rows))
    return {item.get_mark() for item in result["result"].items}


def test_camel_case_omit_occlusion_admits_line_end_to_end():
    """The user-visible symptom: a camelCase key that used to be dropped.

    With occlusion omission on (the default), a raw temporal plot yields
    only non-occluding marks. Turning it off must admit `line` whichever
    way the key is spelled — before the fix the camelCase spelling was
    discarded and the answer set was unchanged.
    """
    assert "line" not in _marks(None)
    assert "line" in _marks({"omitBarLineAreaWithOcclusion": False})
    assert _marks({"omitBarLineAreaWithOcclusion": False}) == _marks(
        {"omit_bar_line_area_with_occlusion": False}
    )
