"""
シミュレーション仕様。
対象: シミュレーション可能ロジックのみ。単勝・複勝、100円換算、発走直前最終オッズ固定。
"""
from enum import Enum
from typing import List


class BetType(Enum):
    WIN = "単勝"
    PLACE = "複勝"


# 賭け金は常に100円換算
BET_UNIT_JPY = 100

# オッズ: 発走直前最終オッズに固定
# 出力項目
SIMULATION_OUTPUTS = [
    "試行回数",
    "回収率",
    "的中率",
    "年別推移",
    "最大ドローダウン",
    "最大連敗数",
]
