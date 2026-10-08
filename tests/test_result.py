"""Tests for the ResultTree container and its traversal helpers."""
from __future__ import annotations

from compassql.result import (
    ResultTree,
    get_top_result_tree_item,
    is_result_tree,
    iter_leaves,
    map_leaves,
)


def _tree(name: str, *items) -> ResultTree:
    return ResultTree(name=name, path=name, items=list(items))


class TestIterLeaves:
    def test_flat_tree_yields_items_in_order(self):
        tree = _tree("root", "a", "b", "c")
        assert list(iter_leaves(tree)) == ["a", "b", "c"]

    def test_empty_tree_yields_nothing(self):
        assert list(iter_leaves(_tree("root"))) == []

    def test_nested_tree_is_flattened_depth_first(self):
        tree = _tree("root", _tree("g1", "a", "b"), _tree("g2", "c"))
        assert list(iter_leaves(tree)) == ["a", "b", "c"]

    def test_deeply_nested_tree(self):
        """nest() adds one level per Nest entry, so depth is unbounded."""
        tree = _tree("root", _tree("g1", _tree("g1a", "a"), _tree("g1b", "b")), "c")
        assert list(iter_leaves(tree)) == ["a", "b", "c"]

    def test_mixed_leaves_and_subtrees_at_one_level(self):
        tree = _tree("root", "a", _tree("g", "b", "c"), "d")
        assert list(iter_leaves(tree)) == ["a", "b", "c", "d"]

    def test_is_lazy(self):
        """A generator, so a caller taking the top N does not walk the rest."""
        tree = _tree("root", *range(1000))
        it = iter_leaves(tree)
        assert [next(it) for _ in range(3)] == [0, 1, 2]

    def test_agrees_with_get_top_result_tree_item(self):
        tree = _tree("root", _tree("g1", "a", "b"), _tree("g2", "c"))
        assert next(iter_leaves(tree)) == get_top_result_tree_item(tree)

    def test_agrees_with_map_leaves(self):
        """Both helpers must see the same leaf set."""
        tree = _tree("root", _tree("g1", 1, 2), _tree("g2", 3))
        mapped = map_leaves(tree, lambda x: x * 10)
        assert list(iter_leaves(mapped)) == [10, 20, 30]


class TestIsResultTree:
    def test_distinguishes_trees_from_leaves(self):
        assert is_result_tree(_tree("t"))
        assert not is_result_tree("a leaf")


class TestIterLeavesOnRealRecommendOutput:
    def test_walks_the_tree_recommend_actually_returns(self):
        import pandas as pd

        from compassql import Schema, recommend
        from compassql.query.encoding import encoding_query_from_dict
        from compassql.query.query import Query
        from compassql.query.spec import SpecQuery

        df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2.0, 4.0, 6.0, 8.0]})
        spec_q = SpecQuery(
            mark="?",
            encodings=[
                encoding_query_from_dict({"channel": "?", "field": "a", "type": "quantitative"}),
                encoding_query_from_dict({"channel": "?", "field": "b", "type": "quantitative"}),
            ],
            data={"values": []},
        )
        result = recommend(
            Query(spec=spec_q, orderBy="effectiveness", config={"autoAddCount": False}),
            Schema.build_from_data(df),
        )

        leaves = list(iter_leaves(result["result"]))
        assert leaves, "recommend() should produce at least one candidate"
        assert all(hasattr(m, "to_spec") for m in leaves)
        assert leaves[0].to_shorthand() == "point|x:a,q|y:b,q"
