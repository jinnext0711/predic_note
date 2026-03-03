"""
ロジック記録の統合モデル。
Scope + Must + Prefer/Avoid + ロジック種別 を1つの「ロジック」として保持。
"""
from typing import List, Optional
from models.scope import RaceScope
from models.must import MustLogic
from models.prefer_avoid import PreferAvoidLogic
from models.custom_variable import CustomVariable
from models.logic_type import LogicType, classify_logic


class LogicRecord:
    """
    1つの予想ロジックの記録。
    シミュレーション可能かどうかはロジック種別で決まる。
    """

    def __init__(
        self,
        name: str,
        scope: RaceScope,
        must: MustLogic,
        prefer_avoid: PreferAvoidLogic,
        custom_variables: Optional[List[CustomVariable]] = None,
        is_selection_only: bool = True,
        uses_internal_data_only: bool = True,
    ):
        self.name = name
        self.scope = scope
        self.must = must
        self.prefer_avoid = prefer_avoid
        self.custom_variables = custom_variables or []
        if len(self.custom_variables) > 3:
            raise ValueError("カスタム変数は最大3個まで")
        self._is_selection_only = is_selection_only
        self._uses_internal_data_only = uses_internal_data_only
        self._logic_type = classify_logic(
            is_selection_only, uses_internal_data_only, self.custom_variables
        )

    @property
    def logic_type(self) -> LogicType:
        return self._logic_type

    @property
    def can_simulate(self) -> bool:
        return self._logic_type == LogicType.SIMULATION_CAPABLE
