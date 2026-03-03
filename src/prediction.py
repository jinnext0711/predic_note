"""
予想エンジン。
simulation.py の関数を再利用して、対象レースに合うロジックで予想を実行する。
"""
from pathlib import Path
from typing import Dict, List, Optional, Any

from data.schema import HorseEntry, Race
from simulation import _race_matches_scope, _entry_passes_must, _rank_entries, _get_entry_value
import logic_store
from auth_store import get_purchased_logics


def find_matching_logics(
    race_info: dict,
    username: str,
    base_path: Path = None,
) -> List[dict]:
    """
    Scope条件がレースに一致するロジック一覧を返す。
    自分のロジック + 購入済みロジック を対象にする。
    race_info: {venue, distance, surface, race_class, age_condition}
    """
    # レース情報をRaceオブジェクトに変換（マッチング用）
    from datetime import date
    race = Race(
        race_id="prediction",
        date=date.today(),
        venue=race_info.get("venue", ""),
        distance=int(race_info.get("distance", 0)),
        surface=race_info.get("surface", ""),
        race_class=race_info.get("race_class", ""),
        age_condition=race_info.get("age_condition", ""),
    )

    all_logics = logic_store.load_all(base_path)
    purchased_keys = get_purchased_logics(username, base_path)

    matching = []
    for rec in all_logics:
        owner = rec.get("owner", "")
        name = rec.get("name", "")
        key = f"{owner}::{name}"

        # 自分のロジック or 購入済みロジックのみ
        is_own = (owner == username)
        is_purchased = (key in purchased_keys)
        if not is_own and not is_purchased:
            continue

        # Scope マッチング
        scope = rec.get("scope", {})
        if not scope:
            continue
        if _race_matches_scope(race, scope):
            # メタ情報を付加
            rec_with_meta = dict(rec)
            rec_with_meta["_is_own"] = is_own
            rec_with_meta["_logic_key"] = key
            matching.append(rec_with_meta)

    return matching


def run_prediction(
    logic_record: dict,
    race_entries: List[HorseEntry],
) -> Optional[HorseEntry]:
    """
    ロジックで予想を実行。Must→Prefer/Avoid→推奨馬（1位）を返す。
    該当馬がいない場合はNone。
    """
    must = logic_record.get("must")
    prefer_avoid = logic_record.get("prefer_avoid")

    # Mustフィルタ
    passed = [e for e in race_entries if _entry_passes_must(e, must)]
    if not passed:
        return None

    # Prefer/Avoidでランキング → 1位を返す
    ranked = _rank_entries(passed, prefer_avoid)
    return ranked[0] if ranked else None


def get_required_categories(logic_record: dict) -> List[str]:
    """
    ロジックが使用するカテゴリ一覧を返す。
    出走馬入力時にどの項目が必要かを判断するために使用。
    """
    categories = set()

    # Mustのカテゴリ
    must = logic_record.get("must")
    if must and must.get("blocks"):
        for block in must["blocks"]:
            for cond in block.get("conditions", []):
                cat = cond.get("category", "")
                if cat:
                    categories.add(cat)

    # Prefer/Avoidのカテゴリ
    pa = logic_record.get("prefer_avoid")
    if pa:
        for p in pa.get("prefer", []):
            cat = p.get("criteria", {}).get("category", "")
            if cat:
                categories.add(cat)
        for a in pa.get("avoid", []):
            cat = a.get("criteria", {}).get("category", "")
            if cat:
                categories.add(cat)

    return sorted(categories)


def build_horse_entry(
    race_id: str,
    horse_number: int,
    horse_name: str,
    final_odds: Optional[float] = None,
    weight: Optional[float] = None,
    previous_order: Optional[int] = None,
    previous_distance: Optional[int] = None,
    previous_position_4c: Optional[int] = None,
) -> HorseEntry:
    """UI入力からHorseEntryオブジェクトに変換する。"""
    return HorseEntry(
        entry_id=f"{race_id}_{horse_number}",
        race_id=race_id,
        frame_number=0,  # 予想時は枠番不要
        horse_number=horse_number,
        horse_name=horse_name,
        previous_order=previous_order,
        previous_position_4c=previous_position_4c,
        previous_distance=previous_distance,
        weight=weight,
        final_odds=final_odds,
        result_order=None,  # 結果は未定
    )
