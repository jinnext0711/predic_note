"""
マーケットプレイス永続化ストア。
出品・購入・売上管理を行う。データは data/marketplace.json に保持。
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from models.marketplace import MarketplaceListing


def _marketplace_path(base: Path = None) -> Path:
    if base is None:
        base = Path(__file__).resolve().parent.parent
    return base / "data" / "marketplace.json"


def _load_data(base_path: Path = None) -> dict:
    """マーケットプレイスデータを読み込む。"""
    path = _marketplace_path(base_path)
    if not path.exists():
        return {"listings": {}, "sales": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("listings", {})
        data.setdefault("sales", [])
        return data
    except (json.JSONDecodeError, OSError):
        return {"listings": {}, "sales": []}


def _save_data(data: dict, base_path: Path = None) -> None:
    """マーケットプレイスデータを保存する。"""
    path = _marketplace_path(base_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_marketplace(
    logic_key: str,
    seller: str,
    price: int,
    description_short: str,
    backtest_win: dict,
    backtest_place: dict,
    base_path: Path = None,
) -> bool:
    """アルゴリズムをマーケットプレイスに出品する。"""
    data = _load_data(base_path)
    if logic_key in data["listings"]:
        return False  # 既に出品済み
    data["listings"][logic_key] = {
        "seller": seller,
        "price": price,
        "description_short": description_short,
        "listed_at": datetime.now().isoformat(timespec="seconds"),
        "backtest_win": backtest_win,
        "backtest_place": backtest_place,
        "purchase_count": 0,
    }
    _save_data(data, base_path)
    return True


def delist_marketplace(logic_key: str, base_path: Path = None) -> bool:
    """出品を取り下げる。"""
    data = _load_data(base_path)
    if logic_key not in data["listings"]:
        return False
    del data["listings"][logic_key]
    _save_data(data, base_path)
    return True


def update_listing_price(logic_key: str, new_price: int, base_path: Path = None) -> bool:
    """出品中アルゴリズムの価格を変更する。"""
    data = _load_data(base_path)
    listing = data["listings"].get(logic_key)
    if listing is None:
        return False
    listing["price"] = new_price
    _save_data(data, base_path)
    return True


def load_listings(base_path: Path = None) -> Dict[str, dict]:
    """出品一覧を辞書で返す。{logic_key: listing_dict}"""
    data = _load_data(base_path)
    return dict(data.get("listings", {}))


def get_listing(logic_key: str, base_path: Path = None) -> Optional[dict]:
    """特定の出品情報を返す。"""
    data = _load_data(base_path)
    return data["listings"].get(logic_key)


def is_listed(logic_key: str, base_path: Path = None) -> bool:
    """出品中か確認。"""
    data = _load_data(base_path)
    return logic_key in data["listings"]


def purchase_logic(buyer: str, logic_key: str, base_path: Path = None) -> tuple:
    """
    購入処理。ポイント消費 + purchased_logics追加 + 売り手にポイント加算。
    戻り値: (成功したか, メッセージ)
    """
    from auth_store import add_purchased_logic, get_purchased_logics
    from point_store import get_points, deduct_points, add_points

    # 出品情報取得
    data = _load_data(base_path)
    listing = data["listings"].get(logic_key)
    if listing is None:
        return False, "この商品は見つかりません。"

    seller = listing["seller"]
    price = int(listing["price"])

    # 自分の出品は購入不可
    if buyer == seller:
        return False, "自分のアルゴリズムは購入できません。"

    # 購入済みチェック
    purchased = get_purchased_logics(buyer, base_path)
    if logic_key in purchased:
        return False, "既に購入済みです。"

    # ポイント残高チェック
    current_points = get_points(buyer, base_path)
    if current_points < price:
        return False, f"ポイントが不足しています（残高: {current_points}pt、価格: {price}pt）。"

    # ポイント消費
    if not deduct_points(buyer, price, f"マーケットプレイス購入: {logic_key}", base_path):
        return False, "ポイントの消費に失敗しました。"

    # 売り手にポイント加算
    add_points(seller, price, f"マーケットプレイス売上: {logic_key}", base_path)

    # 購入済みリストに追加
    add_purchased_logic(buyer, logic_key, base_path)

    # 購入数カウントアップ
    listing["purchase_count"] = int(listing.get("purchase_count", 0)) + 1
    _save_data(data, base_path)

    # 売上履歴に追加
    data["sales"].append({
        "logic_key": logic_key,
        "buyer": buyer,
        "seller": seller,
        "price": price,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    _save_data(data, base_path)

    return True, f"購入が完了しました（{price}pt消費）。"


def is_purchased(username: str, logic_key: str, base_path: Path = None) -> bool:
    """購入済みか確認。"""
    from auth_store import get_purchased_logics
    return logic_key in get_purchased_logics(username, base_path)


def get_seller_sales(username: str, base_path: Path = None) -> List[dict]:
    """指定ユーザーの売上履歴を返す。"""
    data = _load_data(base_path)
    return [s for s in data.get("sales", []) if s.get("seller") == username]
