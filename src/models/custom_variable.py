"""
カスタム変数（最大3個）。含む場合はシミュレーション不可。
"""
from typing import List, Union, Optional
from enum import Enum

CUSTOM_VAR_MAX = 3

# 3段階カテゴリの選択肢
THREE_LEVEL_OPTIONS = ["高", "中", "低"]


class CustomVarType(Enum):
    BOOLEAN = "真偽値"
    THREE_LEVEL = "3段階カテゴリ"
    NUMERIC = "数値"


CUSTOM_VAR_TYPE_LIST = [t.value for t in CustomVarType]


class CustomVariable:
    """カスタム変数1つ。"""

    def __init__(self, name: str, var_type: CustomVarType, default_value: Union[bool, str, int, float] = None):
        self.name = name
        self.var_type = var_type
        self.default_value = default_value

    def is_valid(self) -> bool:
        return bool(self.name) and self.var_type in CustomVarType

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "var_type": self.var_type.value,
            "default_value": self.default_value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CustomVariable":
        vt_str = d.get("var_type", CustomVarType.BOOLEAN.value)
        var_type = next((t for t in CustomVarType if t.value == vt_str), CustomVarType.BOOLEAN)
        return cls(
            name=d.get("name", ""),
            var_type=var_type,
            default_value=d.get("default_value"),
        )


class CustomVariableSet:
    """カスタム変数セット（最大3個）。"""

    def __init__(self, variables: Optional[List[CustomVariable]] = None):
        self.variables = list(variables) if variables else []
        if len(self.variables) > CUSTOM_VAR_MAX:
            raise ValueError(f"カスタム変数は最大{CUSTOM_VAR_MAX}個まで")

    def to_dict(self) -> dict:
        return {"variables": [v.to_dict() for v in self.variables]}

    @classmethod
    def from_dict(cls, d: dict) -> "CustomVariableSet":
        variables = [CustomVariable.from_dict(v) for v in d.get("variables", [])]
        return cls(variables=variables)
