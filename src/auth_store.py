"""
ユーザー認証の永続化（タスク 6.1）。
ユーザー登録・ログイン・パスワードハッシュ化。データは JSON ファイルで保持。
"""
import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


def _users_path(base: Path = None) -> Path:
    if base is None:
        base = Path(__file__).resolve().parent.parent
    return base / "data" / "users.json"


def _hash_password(password: str, salt: str) -> str:
    """パスワードを salt 付き SHA-256 でハッシュ化する。"""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _load_users(base_path: Path = None) -> dict:
    """ユーザーデータを読み込む。{"users": {username: {salt, password_hash, ...}}}"""
    path = _users_path(base_path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("users", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict, base_path: Path = None) -> None:
    """ユーザーデータを保存する。"""
    path = _users_path(base_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)


def register_user(username: str, password: str, base_path: Path = None) -> Tuple[bool, str]:
    """
    ユーザー登録。
    戻り値: (成功したか, メッセージ)
    """
    username = username.strip()
    if not username:
        return False, "ユーザー名を入力してください。"
    if len(username) < 3:
        return False, "ユーザー名は3文字以上にしてください。"
    if len(password) < 6:
        return False, "パスワードは6文字以上にしてください。"

    users = _load_users(base_path)
    if username in users:
        return False, "このユーザー名は既に使用されています。"

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)
    users[username] = {
        "salt": salt,
        "password_hash": password_hash,
        "is_paid": False,
        "backtest_count": 0,
        "points": 1000,
        "point_history": [
            {"amount": 1000, "reason": "初回ボーナス",
             "at": datetime.now().isoformat(timespec="seconds")}
        ],
        "purchased_logics": [],
    }
    _save_users(users, base_path)
    return True, "登録が完了しました。"


def authenticate_user(username: str, password: str, base_path: Path = None) -> Tuple[bool, str]:
    """
    ログイン認証。
    戻り値: (成功したか, メッセージ)
    """
    username = username.strip()
    if not username or not password:
        return False, "ユーザー名とパスワードを入力してください。"

    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return False, "ユーザー名またはパスワードが正しくありません。"

    salt = user.get("salt", "")
    expected_hash = user.get("password_hash", "")
    actual_hash = _hash_password(password, salt)

    if actual_hash != expected_hash:
        return False, "ユーザー名またはパスワードが正しくありません。"

    return True, "ログインしました。"


# 他人の公開ロジックのバックテスト回数制限（無料ユーザー）
FREE_BACKTEST_LIMIT = 3


def is_paid_user(username: str, base_path: Path = None) -> bool:
    """ユーザーが有料プランかどうかを返す。"""
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return False
    return bool(user.get("is_paid", False))


def get_backtest_count(username: str, base_path: Path = None) -> int:
    """ユーザーのバックテスト実行回数を返す。"""
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return 0
    return int(user.get("backtest_count", 0))


def increment_backtest_count(username: str, base_path: Path = None) -> int:
    """バックテスト実行回数を1増やして、新しい値を返す。"""
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return 0
    user["backtest_count"] = int(user.get("backtest_count", 0)) + 1
    _save_users(users, base_path)
    return user["backtest_count"]


def can_run_backtest(username: str, is_own_logic: bool, base_path: Path = None) -> Tuple[bool, str]:
    """
    バックテスト実行可否を判定する。
    - 有料ユーザー: 自分のロジックは無制限、他人のロジックも無制限
    - 無料ユーザー: 自分のロジックは不可、他人の公開ロジックは回数制限あり
    戻り値: (実行可否, 理由メッセージ)
    """
    paid = is_paid_user(username, base_path)

    if paid:
        return True, ""

    # 無料ユーザー
    if is_own_logic:
        return False, "自分のロジックのバックテストは有料プランでのみ利用できます。"

    # 他人の公開ロジック: 回数制限チェック
    count = get_backtest_count(username, base_path)
    if count >= FREE_BACKTEST_LIMIT:
        return False, f"無料プランのバックテスト回数制限（{FREE_BACKTEST_LIMIT}回）に達しました。有料プランにアップグレードしてください。"

    remaining = FREE_BACKTEST_LIMIT - count
    return True, f"無料プラン: 残り{remaining}回実行可能"


# ── 購入済みロジック管理 ──

def get_purchased_logics(username: str, base_path: Path = None) -> List[str]:
    """購入済みロジックキー一覧を返す。"""
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return []
    return list(user.get("purchased_logics", []))


def add_purchased_logic(username: str, logic_key: str, base_path: Path = None) -> bool:
    """購入済みリストにロジックキーを追加。既に購入済みならFalse。"""
    users = _load_users(base_path)
    user = users.get(username)
    if user is None:
        return False
    purchased = user.setdefault("purchased_logics", [])
    if logic_key in purchased:
        return False
    purchased.append(logic_key)
    _save_users(users, base_path)
    return True
