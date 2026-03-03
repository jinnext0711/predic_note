"""
血統データ（5世代対応）。生の血統ツリーは編集不可。ロジックで使えるのは事前定義指標のみ。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class BloodlineIndicators:
    """
    事前定義された血統指標。Must 等のロジックで使用可能。
    5世代血統から導出され、生ツリーはロジックから触らない。
    """
    sire_line: Optional[str] = None          # 父系カテゴリ（サンデーサイレンス系 等）
    broodmare_sire_line: Optional[str] = None  # 母父系カテゴリ
    distance_aptitude: Optional[str] = None   # 距離適性（短距離寄り / 中距離寄り / 長距離寄り）
    surface_aptitude: Optional[str] = None    # 芝/ダート適性（芝向き / ダート向き / 両対応）
    inbreed_3x4_or_closer: Optional[str] = None  # 3×4以内クロス有無（あり / なし）
    inbreed_cross_count_band: Optional[str] = None  # クロス本数区分（0本 / 1本 / 2本以上）

    def to_dict(self) -> dict:
        return {
            "sire_line": self.sire_line,
            "broodmare_sire_line": self.broodmare_sire_line,
            "distance_aptitude": self.distance_aptitude,
            "surface_aptitude": self.surface_aptitude,
            "inbreed_3x4_or_closer": self.inbreed_3x4_or_closer,
            "inbreed_cross_count_band": self.inbreed_cross_count_band,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BloodlineIndicators":
        return cls(
            sire_line=d.get("sire_line"),
            broodmare_sire_line=d.get("broodmare_sire_line"),
            distance_aptitude=d.get("distance_aptitude"),
            surface_aptitude=d.get("surface_aptitude"),
            inbreed_3x4_or_closer=d.get("inbreed_3x4_or_closer"),
            inbreed_cross_count_band=d.get("inbreed_cross_count_band"),
        )


class BloodlineFetcher(ABC):
    """血統指標の取得インターフェース。5世代データから事前定義指標のみ返す。"""

    @abstractmethod
    def get_indicators(self, horse_id: str) -> Optional[BloodlineIndicators]:
        """馬IDに対応する血統指標を取得する。"""
        pass


class StubBloodlineFetcher(BloodlineFetcher):
    """スタブ実装。実データは取得せず None を返す。"""

    def get_indicators(self, horse_id: str) -> Optional[BloodlineIndicators]:
        return None
