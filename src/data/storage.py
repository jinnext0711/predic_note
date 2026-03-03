"""
レース・馬データの保存・読み込み（MVP: JSON を data/ 以下に保存）。
"""
import json
from datetime import date
from pathlib import Path
from typing import List

from .schema import Race, HorseEntry, RaceWithEntries
from .bloodline import BloodlineIndicators


def _data_dir(base: Path = None) -> Path:
    """データ保存先ディレクトリ。プロジェクトルートの data/ を想定。"""
    if base is None:
        base = Path(__file__).resolve().parent.parent.parent  # predic_keiba ルート
    d = base / "data" / "races"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_races(races: List[Race], base_path: Path = None, merge: bool = True) -> Path:
    """
    レース一覧を JSON で保存する。
    merge=True のとき既存レースを読み込み、同一 race_id は上書き・新規は追加する（増分取得で既存が消えないようにする）。
    """
    data_dir = _data_dir(base_path)
    path = data_dir / "races.json"
    if merge and path.exists():
        existing = {r.race_id: r for r in load_races(base_path)}
        for r in races:
            existing[r.race_id] = r
        races = list(existing.values())
    data = [r.to_dict() for r in races]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_races(base_path: Path = None) -> List[Race]:
    """保存済みのレース一覧を読み込む。"""
    data_dir = _data_dir(base_path)
    path = data_dir / "races.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Race.from_dict(d) for d in data]


def save_entries(race_id: str, entries: List[HorseEntry], base_path: Path = None) -> Path:
    """指定レースの出走馬一覧を JSON で保存する。"""
    data_dir = _data_dir(base_path)
    safe_id = race_id.replace("/", "_").replace("\\", "_")
    path = data_dir / f"entries_{safe_id}.json"
    data = [e.to_dict() for e in entries]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_entries(race_id: str, base_path: Path = None) -> List[HorseEntry]:
    """保存済みの出走馬一覧を読み込む。"""
    data_dir = _data_dir(base_path)
    safe_id = race_id.replace("/", "_").replace("\\", "_")
    path = data_dir / f"entries_{safe_id}.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [HorseEntry.from_dict(d) for d in data]


def update_entries_odds(
    race_id: str,
    entry_id_to_odds: dict,
    base_path: Path = None,
) -> bool:
    """
    保存済み出走馬の final_odds のみ更新する（オッズ取得・紐付け用）。
    entry_id_to_odds: { entry_id: 倍率(float) }
    戻り値: 更新した場合 True。
    """
    entries = load_entries(race_id, base_path)
    if not entries:
        return False
    updated = []
    for e in entries:
        odds = entry_id_to_odds.get(e.entry_id)
        updated.append(
            HorseEntry(
                entry_id=e.entry_id,
                race_id=e.race_id,
                frame_number=e.frame_number,
                horse_number=e.horse_number,
                horse_name=e.horse_name,
                previous_order=e.previous_order,
                previous_position_4c=e.previous_position_4c,
                previous_distance=e.previous_distance,
                weight=e.weight,
                final_odds=float(odds) if odds is not None else e.final_odds,
                result_order=e.result_order,
            )
        )
    save_entries(race_id, updated, base_path)
    return True


def _bloodline_dir(base: Path = None) -> Path:
    """血統指標の保存先。"""
    if base is None:
        base = Path(__file__).resolve().parent.parent.parent
    d = base / "data" / "bloodline"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_bloodline_indicators(horse_id: str, indicators: BloodlineIndicators, base_path: Path = None) -> Path:
    """馬ごとの血統指標を JSON で保存する。"""
    data_dir = _bloodline_dir(base_path)
    safe_id = horse_id.replace("/", "_").replace("\\", "_")
    path = data_dir / f"{safe_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(indicators.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def load_bloodline_indicators(horse_id: str, base_path: Path = None) -> BloodlineIndicators:
    """保存済みの血統指標を読み込む。無ければ None でない空の指標を返す。"""
    data_dir = _bloodline_dir(base_path)
    safe_id = horse_id.replace("/", "_").replace("\\", "_")
    path = data_dir / f"{safe_id}.json"
    if not path.exists():
        return BloodlineIndicators()
    with open(path, "r", encoding="utf-8") as f:
        return BloodlineIndicators.from_dict(json.load(f))
