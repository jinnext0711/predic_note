"""
前走データ計算バッチ。

全レース結果を時系列で蓄積した後、各出走馬の前走データ
（前走着順・前走4角位置・前走距離）を逆算して埋める。

方針B: 全レース蓄積後に前走データを自前で計算（netkeiba負荷最小）。
"""
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .schema import Race, HorseEntry
from . import storage

logger = logging.getLogger(__name__)


def _parse_passing_order(passing_text: str) -> Optional[int]:
    """
    通過順テキストから4角位置を取得する。
    例: '4-3-6-4' -> 4（最後の数値が4角位置）
    """
    if not passing_text:
        return None
    parts = passing_text.split("-")
    if len(parts) >= 4:
        try:
            return int(parts[3].strip())
        except (ValueError, IndexError):
            return None
    return None


def compute_previous_race_data(base_path: Optional[Path] = None) -> int:
    """
    全保存済みレースから前走データを計算し、各エントリーに設定する。

    処理:
    1. 全レースを日付順にソート
    2. 馬名ごとに出走履歴を時系列で構築
    3. 各エントリーに前走着順・前走距離を設定
    4. 更新したエントリーを保存

    戻り値: 更新したレース数。
    """
    races = storage.load_races(base_path)
    if not races:
        return 0

    # 日付順にソート
    races.sort(key=lambda r: r.date)

    # 馬名 -> [(race_date, race_id, result_order, distance, position_4c)] の履歴
    horse_history: Dict[str, List[Tuple]] = defaultdict(list)

    updated_count = 0

    for race in races:
        entries = storage.load_entries(race.race_id, base_path)
        if not entries:
            continue

        modified = False
        new_entries: List[HorseEntry] = []

        for entry in entries:
            # 前走データを履歴から取得
            prev_order = None
            prev_distance = None
            prev_position_4c = None

            history = horse_history.get(entry.horse_name, [])
            if history:
                # 最新の履歴（= 直近の出走）を前走とする
                last = history[-1]
                prev_order = last[2]       # result_order
                prev_distance = last[3]    # distance
                prev_position_4c = last[4] # position_4c

            # 値が変わった場合のみ更新
            if (entry.previous_order != prev_order or
                    entry.previous_distance != prev_distance or
                    entry.previous_position_4c != prev_position_4c):
                entry = HorseEntry(
                    entry_id=entry.entry_id,
                    race_id=entry.race_id,
                    frame_number=entry.frame_number,
                    horse_number=entry.horse_number,
                    horse_name=entry.horse_name,
                    previous_order=prev_order,
                    previous_position_4c=prev_position_4c,
                    previous_distance=prev_distance,
                    weight=entry.weight,
                    final_odds=entry.final_odds,
                    result_order=entry.result_order,
                )
                modified = True

            new_entries.append(entry)

        # このレースの全エントリーを履歴に追加（着順がある馬のみ）
        for entry in new_entries:
            if entry.result_order is not None:
                horse_history[entry.horse_name].append((
                    race.date,
                    race.race_id,
                    entry.result_order,
                    race.distance,
                    None,  # 4角位置はレース結果ページの通過順から取得する必要あり（将来拡張）
                ))

        # 変更があれば保存
        if modified:
            storage.save_entries(race.race_id, new_entries, base_path)
            updated_count += 1

    logger.info("前走データ更新: %d / %d レース", updated_count, len(races))
    return updated_count
