"""logic_store.py のテスト（永続化・CRUD操作）。"""
import json
import pytest
from pathlib import Path

from logic_store import (
    save_scope,
    save_must,
    save_prefer_avoid,
    save_custom_vars,
    load_scope,
    load_must,
    load_prefer_avoid,
    load_custom_vars,
    load_all,
    list_names,
    set_public,
    list_public_logics,
    delete_logic,
    save_forward_result,
    load_forward_record,
    delete_forward_result,
)
from models.scope import RaceScope
from models.must import MustLogic, MustBlock
from models.prefer_avoid import PreferAvoidLogic, PreferCondition, AvoidCondition
from models.custom_variable import CustomVariableSet, CustomVariable, CustomVarType
from models.forward_record import ForwardResult


# ── Scope の保存・読み込み ──

class TestScopePersistence:
    def test_save_and_load_scope(self, tmp_path):
        """Scope を保存して読み込めることを確認。"""
        scope = RaceScope(
            venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
            race_class=["3勝"], age_condition=["3歳以上"],
        )
        save_scope("テスト", scope, owner="user1", base_path=tmp_path)
        loaded = load_scope("テスト", base_path=tmp_path)
        assert loaded is not None
        assert loaded.venues == ["東京"]
        assert loaded.distance_min == 1400
        assert loaded.distance_max == 1800

    def test_save_scope_preserves_existing_data(self, tmp_path):
        """Scope を上書きしても Must/Prefer-Avoid は維持される。"""
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope, owner="user1", base_path=tmp_path)

        # Must を保存
        must = MustLogic(blocks=[MustBlock(conditions=[{"category": "斤量", "operator": "le", "value": "57"}])])
        save_must("テスト", must, base_path=tmp_path)

        # Scope を再保存
        scope2 = RaceScope(venues=["阪神"], surface=["ダート"], distance_min=1000, distance_max=1400,
                           race_class=["2勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope2, owner="user1", base_path=tmp_path)

        # Must が維持されていることを確認
        loaded_must = load_must("テスト", base_path=tmp_path)
        assert loaded_must is not None
        assert len(loaded_must.blocks) == 1

    def test_save_scope_preserves_custom_vars(self, tmp_path):
        """Scope を再保存しても custom_vars が消失しないことを確認（バグ修正テスト）。"""
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope, owner="user1", base_path=tmp_path)

        # カスタム変数を保存
        cv_set = CustomVariableSet(variables=[
            CustomVariable(name="気分", var_type=CustomVarType.BOOLEAN, default_value=True),
            CustomVariable(name="馬場読み", var_type=CustomVarType.THREE_LEVEL, default_value="高"),
        ])
        save_custom_vars("テスト", cv_set, base_path=tmp_path)

        # Scope を再保存
        scope2 = RaceScope(venues=["阪神"], surface=["ダート"], distance_min=1000, distance_max=1400,
                           race_class=["2勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope2, owner="user1", base_path=tmp_path)

        # カスタム変数が維持されていることを確認
        loaded_cv = load_custom_vars("テスト", base_path=tmp_path)
        assert loaded_cv is not None
        assert len(loaded_cv.variables) == 2
        assert loaded_cv.variables[0].name == "気分"
        assert loaded_cv.variables[1].name == "馬場読み"

        # Scope は更新されていることを確認
        loaded_scope = load_scope("テスト", base_path=tmp_path)
        assert loaded_scope.venues == ["阪神"]

    def test_save_scope_preserves_all_fields(self, tmp_path):
        """Scope 再保存で must, prefer_avoid, custom_vars, is_public がすべて保持されることを確認。"""
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("全保持テスト", scope, owner="user1", base_path=tmp_path)

        # 各フィールドを保存
        must = MustLogic(blocks=[MustBlock(conditions=[{"category": "斤量", "operator": "le", "value": "57"}])])
        save_must("全保持テスト", must, base_path=tmp_path)

        pa = PreferAvoidLogic(
            prefer=[PreferCondition(order=1, name="軽斤量",
                                    criteria={"category": "斤量", "operator": "le", "value": "56"})],
            avoid=[],
        )
        save_prefer_avoid("全保持テスト", pa, base_path=tmp_path)

        cv_set = CustomVariableSet(variables=[
            CustomVariable(name="気分", var_type=CustomVarType.BOOLEAN, default_value=False),
        ])
        save_custom_vars("全保持テスト", cv_set, base_path=tmp_path)

        set_public("全保持テスト", True, base_path=tmp_path)

        # Scope を再保存
        scope2 = RaceScope(venues=["中山"], surface=["芝"], distance_min=1800, distance_max=2400,
                           race_class=["OP"], age_condition=["3歳以上"])
        save_scope("全保持テスト", scope2, owner="user1", base_path=tmp_path)

        # 全フィールドが保持されていることを確認
        loaded_must = load_must("全保持テスト", base_path=tmp_path)
        assert loaded_must is not None
        assert len(loaded_must.blocks) == 1

        loaded_pa = load_prefer_avoid("全保持テスト", base_path=tmp_path)
        assert loaded_pa is not None
        assert len(loaded_pa.prefer) == 1

        loaded_cv = load_custom_vars("全保持テスト", base_path=tmp_path)
        assert loaded_cv is not None
        assert len(loaded_cv.variables) == 1

        public_list = list_public_logics(base_path=tmp_path)
        assert len(public_list) == 1

    def test_load_scope_nonexistent(self, tmp_path):
        """存在しないロジック名では None が返る。"""
        result = load_scope("存在しない", base_path=tmp_path)
        assert result is None


# ── Must の保存・読み込み ──

class TestMustPersistence:
    def test_save_and_load_must(self, tmp_path):
        """Must を保存して読み込めることを確認。"""
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope, base_path=tmp_path)

        must = MustLogic(blocks=[
            MustBlock(conditions=[{"category": "斤量", "operator": "le", "value": "57"}]),
            MustBlock(conditions=[{"category": "前走着順", "operator": "le", "value": "3"}]),
        ])
        save_must("テスト", must, base_path=tmp_path)
        loaded = load_must("テスト", base_path=tmp_path)
        assert loaded is not None
        assert len(loaded.blocks) == 2

    def test_save_must_without_scope_does_nothing(self, tmp_path):
        """Scope が保存されていない場合、Must の保存は何もしない。"""
        must = MustLogic(blocks=[MustBlock(conditions=[{"category": "斤量", "operator": "le", "value": "57"}])])
        save_must("存在しない", must, base_path=tmp_path)
        loaded = load_must("存在しない", base_path=tmp_path)
        assert loaded is None


# ── Prefer/Avoid の保存・読み込み ──

class TestPreferAvoidPersistence:
    def test_save_and_load_prefer_avoid(self, tmp_path):
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope, base_path=tmp_path)

        pa = PreferAvoidLogic(
            prefer=[PreferCondition(order=1, name="軽斤量",
                                    criteria={"category": "斤量", "operator": "le", "value": "56"})],
            avoid=[AvoidCondition(name="大外枠",
                                  criteria={"category": "枠番／馬番", "operator": "gt", "value": "14"})],
        )
        save_prefer_avoid("テスト", pa, base_path=tmp_path)
        loaded = load_prefer_avoid("テスト", base_path=tmp_path)
        assert loaded is not None
        assert len(loaded.prefer) == 1
        assert len(loaded.avoid) == 1


# ── カスタム変数の保存・読み込み ──

class TestCustomVarsPersistence:
    def test_save_and_load_custom_vars(self, tmp_path):
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope, base_path=tmp_path)

        cv_set = CustomVariableSet(variables=[
            CustomVariable(name="気分", var_type=CustomVarType.BOOLEAN, default_value=True),
        ])
        save_custom_vars("テスト", cv_set, base_path=tmp_path)
        loaded = load_custom_vars("テスト", base_path=tmp_path)
        assert loaded is not None
        assert len(loaded.variables) == 1
        assert loaded.variables[0].name == "気分"

    def test_load_custom_vars_not_set(self, tmp_path):
        """カスタム変数が未設定の場合は None が返る。"""
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("テスト", scope, base_path=tmp_path)
        loaded = load_custom_vars("テスト", base_path=tmp_path)
        assert loaded is None


# ── 一覧・削除・公開 ──

class TestLogicListAndDelete:
    def test_list_names(self, tmp_path):
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("ロジック1", scope, base_path=tmp_path)
        save_scope("ロジック2", scope, base_path=tmp_path)
        names = list_names(base_path=tmp_path)
        assert "ロジック1" in names
        assert "ロジック2" in names
        assert len(names) == 2

    def test_list_names_empty(self, tmp_path):
        names = list_names(base_path=tmp_path)
        assert names == []

    def test_delete_logic(self, tmp_path):
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("削除対象", scope, base_path=tmp_path)
        assert "削除対象" in list_names(base_path=tmp_path)

        result = delete_logic("削除対象", base_path=tmp_path)
        assert result is True
        assert "削除対象" not in list_names(base_path=tmp_path)

    def test_delete_nonexistent(self, tmp_path):
        result = delete_logic("存在しない", base_path=tmp_path)
        assert result is False

    def test_set_public(self, tmp_path):
        scope = RaceScope(venues=["東京"], surface=["芝"], distance_min=1400, distance_max=1800,
                          race_class=["3勝"], age_condition=["3歳以上"])
        save_scope("公開テスト", scope, base_path=tmp_path)

        set_public("公開テスト", True, base_path=tmp_path)
        public = list_public_logics(base_path=tmp_path)
        assert len(public) == 1
        assert public[0]["name"] == "公開テスト"

        set_public("公開テスト", False, base_path=tmp_path)
        public = list_public_logics(base_path=tmp_path)
        assert len(public) == 0

    def test_load_all_corrupted_file(self, tmp_path):
        """ファイルが壊れている場合は空リストが返る。"""
        path = tmp_path / "data" / "logics.json"
        path.parent.mkdir(parents=True)
        path.write_text("invalid json{{{")
        result = load_all(base_path=tmp_path)
        assert result == []


# ── フォワード成績 ──

class TestForwardRecordPersistence:
    def test_save_and_load_forward_result(self, tmp_path):
        result = ForwardResult(
            race_id="R001", race_date="2024-06-01", race_name="東京5R",
            bet_type="単勝", horse_name="テスト馬", horse_number=1,
            bet_amount=100, is_hit=True, payout=500.0,
        )
        save_forward_result("テスト", result, base_path=tmp_path)
        record = load_forward_record("テスト", base_path=tmp_path)
        assert record is not None
        assert len(record.results) == 1
        assert record.results[0].horse_name == "テスト馬"
        assert record.results[0].payout == 500.0

    def test_append_forward_results(self, tmp_path):
        """複数回保存すると結果が追加される。"""
        r1 = ForwardResult(
            race_id="R001", race_date="2024-06-01", race_name="東京5R",
            bet_type="単勝", horse_name="馬A", horse_number=1,
            bet_amount=100, is_hit=True, payout=500.0,
        )
        r2 = ForwardResult(
            race_id="R002", race_date="2024-06-02", race_name="東京6R",
            bet_type="複勝", horse_name="馬B", horse_number=2,
            bet_amount=100, is_hit=False, payout=0.0,
        )
        save_forward_result("テスト", r1, base_path=tmp_path)
        save_forward_result("テスト", r2, base_path=tmp_path)
        record = load_forward_record("テスト", base_path=tmp_path)
        assert len(record.results) == 2

    def test_delete_forward_result(self, tmp_path):
        r1 = ForwardResult(
            race_id="R001", race_date="2024-06-01", race_name=None,
            bet_type="単勝", horse_name="馬A", horse_number=1,
            bet_amount=100, is_hit=True, payout=300.0,
        )
        save_forward_result("テスト", r1, base_path=tmp_path)
        result = delete_forward_result("テスト", 0, base_path=tmp_path)
        assert result is True
        record = load_forward_record("テスト", base_path=tmp_path)
        assert len(record.results) == 0

    def test_delete_forward_invalid_index(self, tmp_path):
        result = delete_forward_result("テスト", 0, base_path=tmp_path)
        assert result is False

    def test_load_forward_nonexistent(self, tmp_path):
        record = load_forward_record("存在しない", base_path=tmp_path)
        assert record is None
