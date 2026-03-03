"""RaceScope モデルのテスト。"""
import pytest
from models.scope import RaceScope


class TestRaceScope:
    def test_valid_scope(self):
        scope = RaceScope(
            venues=["東京"],
            surface=["芝"],
            race_class=["3勝"],
            age_condition=["3歳以上"],
            distance_min=1400,
            distance_max=1800,
        )
        assert scope.is_valid()

    def test_invalid_scope_empty_venues(self):
        scope = RaceScope(
            venues=[],
            surface=["芝"],
            race_class=["3勝"],
            age_condition=["3歳以上"],
            distance_min=1400,
            distance_max=1800,
        )
        assert not scope.is_valid()

    def test_invalid_scope_no_distance(self):
        scope = RaceScope(
            venues=["東京"],
            surface=["芝"],
            race_class=["3勝"],
            age_condition=["3歳以上"],
        )
        assert not scope.is_valid()

    def test_to_dict_and_from_dict(self):
        scope = RaceScope(
            venues=["東京", "中山"],
            surface=["芝"],
            race_class=["G1"],
            age_condition=["3歳以上"],
            distance_min=1600,
            distance_max=2400,
        )
        d = scope.to_dict()
        restored = RaceScope.from_dict(d)
        assert restored.venues == ["東京", "中山"]
        assert restored.distance_min == 1600
        assert restored.distance_max == 2400
        assert restored.surface == ["芝"]
        assert restored.race_class == ["G1"]
        assert restored.age_condition == ["3歳以上"]

    def test_from_dict_empty(self):
        scope = RaceScope.from_dict({})
        assert scope.venues == []
        assert not scope.is_valid()

    def test_from_dict_legacy_categories(self):
        """旧距離カテゴリ形式から自動変換されること。"""
        d = {
            "venues": ["東京"],
            "distances": ["マイル"],
            "surface": ["芝"],
            "race_class": ["3勝"],
            "age_condition": ["3歳以上"],
        }
        scope = RaceScope.from_dict(d)
        assert scope.distance_min == 1401
        assert scope.distance_max == 1800
        assert scope.is_valid()

    def test_from_dict_legacy_multiple_categories(self):
        """旧形式で複数カテゴリの場合、最小〜最大の範囲に変換。"""
        d = {
            "venues": ["東京"],
            "distances": ["短距離", "マイル"],
            "surface": ["芝"],
            "race_class": ["3勝"],
            "age_condition": ["3歳以上"],
        }
        scope = RaceScope.from_dict(d)
        assert scope.distance_min == 1000
        assert scope.distance_max == 1800
