"""
予想ロジック Prefer / Avoid モデル。
Must を満たした馬の順位付け。レキシコグラフィック方式。加点方式はMVPでは採用しない。
"""
from typing import List

# Prefer: 最大5個・優先順位・並び替え可能
PREFER_MAX = 5

# Avoid: 最大2個
AVOID_MAX = 2


class PreferCondition:
    """優先する条件。順序で比較（レキシコグラフィック）。"""

    def __init__(self, order: int, name: str, criteria: dict):
        self.order = order  # 1..5
        self.name = name
        self.criteria = dict(criteria) if criteria else {}

    def to_dict(self) -> dict:
        return {"order": self.order, "name": self.name, "criteria": self.criteria}

    @classmethod
    def from_dict(cls, d: dict) -> "PreferCondition":
        return cls(
            order=int(d.get("order", 1)),
            name=d.get("name", ""),
            criteria=d.get("criteria", {}),
        )


class AvoidCondition:
    """順位を下げる条件。"""

    def __init__(self, name: str, criteria: dict):
        self.name = name
        self.criteria = dict(criteria) if criteria else {}

    def to_dict(self) -> dict:
        return {"name": self.name, "criteria": self.criteria}

    @classmethod
    def from_dict(cls, d: dict) -> "AvoidCondition":
        return cls(name=d.get("name", ""), criteria=d.get("criteria", {}))


class PreferAvoidLogic:
    """Prefer / Avoid 全体。"""

    def __init__(
        self,
        prefer: List[PreferCondition],
        avoid: List[AvoidCondition],
    ):
        if len(prefer) > PREFER_MAX:
            raise ValueError(f"Prefer は最大{PREFER_MAX}個まで")
        if len(avoid) > AVOID_MAX:
            raise ValueError(f"Avoid は最大{AVOID_MAX}個まで")
        self.prefer = sorted(prefer, key=lambda x: x.order)
        self.avoid = list(avoid)

    def to_dict(self) -> dict:
        return {
            "prefer": [p.to_dict() for p in self.prefer],
            "avoid": [a.to_dict() for a in self.avoid],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PreferAvoidLogic":
        prefer = [PreferCondition.from_dict(p) for p in d.get("prefer", [])]
        avoid = [AvoidCondition.from_dict(a) for a in d.get("avoid", [])]
        return cls(prefer=prefer, avoid=avoid)
