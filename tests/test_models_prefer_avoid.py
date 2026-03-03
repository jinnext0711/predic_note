"""PreferAvoidLogic モデルのテスト。"""
import pytest
from models.prefer_avoid import (
    PreferCondition, AvoidCondition, PreferAvoidLogic,
    PREFER_MAX, AVOID_MAX,
)


class TestPreferCondition:
    def test_to_dict_and_from_dict(self):
        p = PreferCondition(order=1, name="斤量軽い", criteria={"category": "斤量", "operator": "le", "value": "56"})
        d = p.to_dict()
        restored = PreferCondition.from_dict(d)
        assert restored.order == 1
        assert restored.name == "斤量軽い"
        assert restored.criteria["category"] == "斤量"


class TestAvoidCondition:
    def test_to_dict_and_from_dict(self):
        a = AvoidCondition(name="大外", criteria={"category": "枠番／馬番", "operator": "gt", "value": "6"})
        d = a.to_dict()
        restored = AvoidCondition.from_dict(d)
        assert restored.name == "大外"
        assert restored.criteria["operator"] == "gt"


class TestPreferAvoidLogic:
    def test_valid_logic(self):
        pa = PreferAvoidLogic(
            prefer=[PreferCondition(order=1, name="test", criteria={})],
            avoid=[AvoidCondition(name="test", criteria={})],
        )
        assert len(pa.prefer) == 1
        assert len(pa.avoid) == 1

    def test_prefer_sorted_by_order(self):
        pa = PreferAvoidLogic(
            prefer=[
                PreferCondition(order=3, name="c", criteria={}),
                PreferCondition(order=1, name="a", criteria={}),
                PreferCondition(order=2, name="b", criteria={}),
            ],
            avoid=[],
        )
        assert pa.prefer[0].name == "a"
        assert pa.prefer[1].name == "b"
        assert pa.prefer[2].name == "c"

    def test_prefer_max_exceeded(self):
        with pytest.raises(ValueError):
            PreferAvoidLogic(
                prefer=[PreferCondition(order=i, name=f"p{i}", criteria={}) for i in range(PREFER_MAX + 1)],
                avoid=[],
            )

    def test_avoid_max_exceeded(self):
        with pytest.raises(ValueError):
            PreferAvoidLogic(
                prefer=[],
                avoid=[AvoidCondition(name=f"a{i}", criteria={}) for i in range(AVOID_MAX + 1)],
            )

    def test_to_dict_and_from_dict(self):
        pa = PreferAvoidLogic(
            prefer=[PreferCondition(order=1, name="p1", criteria={"category": "斤量"})],
            avoid=[AvoidCondition(name="a1", criteria={"category": "枠番／馬番"})],
        )
        d = pa.to_dict()
        restored = PreferAvoidLogic.from_dict(d)
        assert len(restored.prefer) == 1
        assert len(restored.avoid) == 1
        assert restored.prefer[0].name == "p1"
