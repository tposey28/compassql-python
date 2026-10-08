"""Vega-Lite type definitions (auto-generated from vega-lite-v5.json schema).
DO NOT EDIT — regenerate with: make regen-types
"""
from enum import Enum


class Mark(str, Enum):
    ARC = "arc"; AREA = "area"; BAR = "bar"; BOXPLOT = "boxplot"
    CIRCLE = "circle"; ERRORBAND = "errorband"; ERRORBAR = "errorbar"
    GEOSHAPE = "geoshape"; IMAGE = "image"; LINE = "line"; POINT = "point"
    RECT = "rect"; RULE = "rule"; SQUARE = "square"; TEXT = "text"
    TICK = "tick"; TRAIL = "trail"


class Channel(str, Enum):
    X = "x"; Y = "y"; X2 = "x2"; Y2 = "y2"
    XOFFSET = "xOffset"; YOFFSET = "yOffset"
    COLOR = "color"; OPACITY = "opacity"; FILLOPACITY = "fillOpacity"
    STROKEOPACITY = "strokeOpacity"; STROKEWIDTH = "strokeWidth"
    SIZE = "size"; SHAPE = "shape"; ROW = "row"; COLUMN = "column"
    FACET = "facet"; TEXT = "text"; TOOLTIP = "tooltip"; HREF = "href"
    KEY = "key"; LATITUDE = "latitude"; LONGITUDE = "longitude"
    LATITUDE2 = "latitude2"; LONGITUDE2 = "longitude2"
    ORDER = "order"; DETAIL = "detail"; DESCRIPTION = "description"


class VLType(str, Enum):
    QUANTITATIVE = "quantitative"; ORDINAL = "ordinal"
    NOMINAL = "nominal"; TEMPORAL = "temporal"; GEOJSON = "geojson"


class ScaleType(str, Enum):
    LINEAR = "linear"; LOG = "log"; POW = "pow"; SQRT = "sqrt"
    SYMLOG = "symlog"; IDENTITY = "identity"; SEQUENTIAL = "sequential"
    TIME = "time"; UTC = "utc"; QUANTILE = "quantile"
    QUANTIZE = "quantize"; THRESHOLD = "threshold"
    BIN_ORDINAL = "bin-ordinal"; ORDINAL = "ordinal"
    POINT = "point"; BAND = "band"


class AggregateOp(str, Enum):
    ARGMAX = "argmax"; ARGMIN = "argmin"; AVERAGE = "average"
    COUNT = "count"; DISTINCT = "distinct"; MAX = "max"; MEAN = "mean"
    MEDIAN = "median"; MIN = "min"; MISSING = "missing"
    PRODUCT = "product"; Q1 = "q1"; Q3 = "q3"
    CI0 = "ci0"; CI1 = "ci1"; STDERR = "stderr"
    STDEV = "stdev"; STDEVP = "stdevp"; SUM = "sum"
    VALID = "valid"; VALUES = "values"; VARIANCE = "variance"; VARIANCEP = "variancep"


class StackOffset(str, Enum):
    ZERO = "zero"; CENTER = "center"; NORMALIZE = "normalize"


class SortOrder(str, Enum):
    ASCENDING = "ascending"; DESCENDING = "descending"


class TimeUnit(str, Enum):
    YEAR = "year"; QUARTER = "quarter"; MONTH = "month"; WEEK = "week"
    DAY = "day"; DAYOFYEAR = "dayofyear"; DATE = "date"
    HOURS = "hours"; MINUTES = "minutes"; SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    YEARQUARTER = "yearquarter"; YEARQUARTERMONTH = "yearquartermonth"
    YEARMONTH = "yearmonth"; YEARMONTHDATE = "yearmonthdate"
    YEARMONTHDATEHOURS = "yearmonthdatehours"
    YEARMONTHDATEHOURSMINUTES = "yearmonthdatehoursminutes"
    YEARMONTHDATEHOURSMINUTESSECONDS = "yearmonthdatehoursminutesseconds"
    QUARTERMONTH = "quartermonth"; MONTHDATE = "monthdate"
    MONTHDATEHOURS = "monthdatehours"; HOURSMINUTES = "hoursminutes"
    HOURSMINUTESSECONDS = "hoursminutesseconds"
    MINUTESSECONDS = "minutesseconds"; SECONDSMILLISECONDS = "secondsmilliseconds"


# Derived constants used throughout the codebase
SUM_OPS: set[AggregateOp] = {
    AggregateOp.SUM, AggregateOp.PRODUCT, AggregateOp.MEAN,
    AggregateOp.AVERAGE, AggregateOp.VARIANCE, AggregateOp.VARIANCEP,
    AggregateOp.STDEV, AggregateOp.STDEVP, AggregateOp.MEDIAN,
    AggregateOp.Q1, AggregateOp.Q3, AggregateOp.CI0, AggregateOp.CI1,
}
NONPOSITION_CHANNELS: set[Channel] = {
    Channel.COLOR, Channel.OPACITY, Channel.SIZE, Channel.SHAPE,
    Channel.TEXT, Channel.TOOLTIP, Channel.HREF, Channel.KEY,
    Channel.ORDER, Channel.DETAIL, Channel.STROKEWIDTH,
    Channel.FILLOPACITY, Channel.STROKEOPACITY,
}
POSITION_FIELD_CHANNELS: set[Channel] = {Channel.X, Channel.Y, Channel.X2, Channel.Y2}
FACET_CHANNELS: set[Channel] = {Channel.ROW, Channel.COLUMN, Channel.FACET}


def has_discrete_domain(scale_type: ScaleType) -> bool:
    return scale_type in {ScaleType.ORDINAL, ScaleType.BAND, ScaleType.POINT, ScaleType.BIN_ORDINAL}


_MARK_CHANNEL_SUPPORT: dict[str, set[str]] = {
    # positional
    "x":           {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    "y":           {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    "x2":          {"area", "bar", "rect", "rule"},
    "y2":          {"area", "bar", "rect", "rule"},
    "xOffset":     {"bar", "circle", "point", "rule", "square", "text", "tick"},
    "yOffset":     {"bar", "circle", "point", "rule", "square", "text", "tick"},
    # non-positional
    "color":       {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail", "geoshape", "arc"},
    "fillOpacity": {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    "opacity":     {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    "shape":       {"circle", "point", "square"},
    "size":        {"circle", "point", "square", "bar", "tick", "rule", "text", "trail"},
    "strokeOpacity":{"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    "strokeWidth": {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick"},
    "text":        {"text"},
    "tooltip":     {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail", "geoshape"},
    "href":        {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick"},
    "url":         {"image"},
    "description": {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    # order / detail
    "order":       {"area", "line", "trail"},
    "detail":      {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    "key":         {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail"},
    # facet
    "row":         {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail", "geoshape"},
    "column":      {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail", "geoshape"},
    "facet":       {"area", "bar", "circle", "line", "point", "rect", "rule", "square", "text", "tick", "trail", "geoshape"},
    # geo
    "latitude":    {"geoshape", "point", "circle", "square"},
    "longitude":   {"geoshape", "point", "circle", "square"},
    "latitude2":   {"geoshape", "point", "circle", "square"},
    "longitude2":  {"geoshape", "point", "circle", "square"},
}


def support_mark(channel: str, mark: str) -> bool:
    """Check if a channel is supported by a mark type (ported from vega-lite channel.ts supportMark)."""
    ch_str = channel.value if isinstance(channel, Channel) else str(channel)
    mk_str = mark.value if isinstance(mark, Mark) else str(mark)
    supported = _MARK_CHANNEL_SUPPORT.get(ch_str)
    if supported is None:
        return True  # unknown channel — allow by default
    return mk_str in supported
