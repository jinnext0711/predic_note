"""
ロジック種別（二車線設計）。
A: シミュレーション可能 / B: シミュレーション不可
"""
from enum import Enum
from typing import List
from .custom_variable import CustomVariable, CUSTOM_VAR_MAX


class LogicType(Enum):
    SIMULATION_CAPABLE = "シミュレーション可能"
    SIMULATION_INCAPABLE = "シミュレーション不可"


def classify_logic(
    is_selection_only: bool,
    uses_internal_data_only: bool,
    custom_variables: List[CustomVariable],
) -> LogicType:
    """
    条件に応じてロジック種別を判定。
    - 完全選択式のみ & 内部データ・導出指標のみ & カスタム変数なし → シミュレーション可能
    - それ以外（自由入力・外部データ・カスタム変数あり）→ シミュレーション不可
    """
    if custom_variables and len(custom_variables) > 0:
        return LogicType.SIMULATION_INCAPABLE
    if not is_selection_only or not uses_internal_data_only:
        return LogicType.SIMULATION_INCAPABLE
    return LogicType.SIMULATION_CAPABLE
