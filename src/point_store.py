"""
ポイント管理ストア。
ユーザーの仮想ポイントを管理する。データは users.json に統合。
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from auth_store import _load_users, _save_users

# 初回登録ボーナス
INITIAL_POINTS = 1000


def get_points(username: str, base_path: Path = None) -> int:
    """現在のポイント残高を返す。"""
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return 0
    return int(user.get("points", 0))


def add_points(username: str, amount: int, reason: str, base_path: Path = None) -> bool:
    """ポイント加算。成功したらTrue。"""
    if amount <= 0:
        return False
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return False
    user["points"] = int(user.get("points", 0)) + amount
    history = user.setdefault("point_history", [])
    history.append({
        "amount": amount,
        "reason": reason,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    _save_users(users, base_path)
    return True


def deduct_points(username: str, amount: int, reason: str, base_path: Path = None) -> bool:
    """ポイント消費。残高不足の場合はFalse。"""
    if amount <= 0:
        return False
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return False
    current = int(user.get("points", 0))
    if current < amount:
        return False
    user["points"] = current - amount
    history = user.setdefault("point_history", [])
    history.append({
        "amount": -amount,
        "reason": reason,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    _save_users(users, base_path)
    return True


def get_point_history(username: str, base_path: Path = None) -> List[dict]:
    """ポイント履歴を返す。"""
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return []
    return list(user.get("point_history", []))
