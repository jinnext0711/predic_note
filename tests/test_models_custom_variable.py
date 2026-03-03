"""CustomVariable / CustomVariableSet モデルのテスト。"""
import pytest
from models.custom_variable import (
    CustomVariable, CustomVariableSet, CustomVarType,
    CUSTOM_VAR_MAX,
)


class TestCustomVariable:
    def test_valid_boolean(self):
        cv = CustomVariable(name="テスト変数", var_type=CustomVarType.BOOLEAN, default_value=True)
        assert cv.is_valid()
        assert cv.name == "テスト変数"
        assert cv.var_type == CustomVarType.BOOLEAN

    def test_valid_numeric(self):
        cv = CustomVariable(name="数値変数", var_type=CustomVarType.NUMERIC, default_value=1.5)
        assert cv.is_valid()

    def test_valid_three_level(self):
        cv = CustomVariable(name="三段階", var_type=CustomVarType.THREE_LEVEL, default_value="高")
        assert cv.is_valid()

    def test_invalid_empty_name(self):
        cv = CustomVariable(name="", var_type=CustomVarType.BOOLEAN)
        assert not cv.is_valid()

    def test_to_dict_and_from_dict(self):
        cv = CustomVariable(name="気分", var_type=CustomVarType.THREE_LEVEL, default_value="中")
        d = cv.to_dict()
        assert d["name"] == "気分"
        assert d["var_type"] == "3段階カテゴリ"
        assert d["default_value"] == "中"

        restored = CustomVariable.from_dict(d)
        assert restored.name == "気分"
        assert restored.var_type == CustomVarType.THREE_LEVEL
        assert restored.default_value == "中"


class TestCustomVariableSet:
    def test_empty_set(self):
        cvs = CustomVariableSet()
        assert len(cvs.variables) == 0

    def test_max_variables(self):
        variables = [
            CustomVariable(name=f"v{i}", var_type=CustomVarType.BOOLEAN)
            for i in range(CUSTOM_VAR_MAX)
        ]
        cvs = CustomVariableSet(variables=variables)
        assert len(cvs.variables) == CUSTOM_VAR_MAX

    def test_max_exceeded(self):
        variables = [
            CustomVariable(name=f"v{i}", var_type=CustomVarType.BOOLEAN)
            for i in range(CUSTOM_VAR_MAX + 1)
        ]
        with pytest.raises(ValueError):
            CustomVariableSet(variables=variables)

    def test_to_dict_and_from_dict(self):
        cvs = CustomVariableSet(variables=[
            CustomVariable(name="v1", var_type=CustomVarType.BOOLEAN, default_value=False),
        ])
        d = cvs.to_dict()
        restored = CustomVariableSet.from_dict(d)
        assert len(restored.variables) == 1
        assert restored.variables[0].name == "v1"
