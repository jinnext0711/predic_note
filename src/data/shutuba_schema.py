"""
出馬表（未来レース）用の拡張スキーマ定義。

既存の Race スキーマを再利用しつつ、出馬表・馬歴・騎手・調教師・オッズを網羅する。
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class UpcomingHorseEntry:
    """出馬表の1頭の情報（未来レース用）。"""

    entry_id: str           # レース内で一意（race_id + 馬番）
    race_id: str
    frame_number: int       # 枠番
    horse_number: int       # 馬番
    horse_name: str
    horse_id: str           # netkeiba horse_id（戦績検索用）
    sex_age: str            # 性齢（牡3, 牝4 等）
    weight_carry: float     # 斤量
    jockey_name: str
    jockey_id: str          # netkeiba jockey_id
    trainer_name: str
    trainer_id: str         # netkeiba trainer_id
    horse_weight: Optional[str] = None       # 馬体重（発表前は None）
    morning_odds: Optional[float] = None     # 前日オッズ
    popularity: Optional[int] = None         # 人気順

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "race_id": self.race_id,
            "frame_number": self.frame_number,
            "horse_number": self.horse_number,
            "horse_name": self.horse_name,
            "horse_id": self.horse_id,
            "sex_age": self.sex_age,
            "weight_carry": self.weight_carry,
            "jockey_name": self.jockey_name,
            "jockey_id": self.jockey_id,
            "trainer_name": self.trainer_name,
            "trainer_id": self.trainer_id,
            "horse_weight": self.horse_weight,
            "morning_odds": self.morning_odds,
            "popularity": self.popularity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UpcomingHorseEntry":
        return cls(
            entry_id=d["entry_id"],
            race_id=d["race_id"],
            frame_number=int(d["frame_number"]),
            horse_number=int(d["horse_number"]),
            horse_name=d["horse_name"],
            horse_id=d["horse_id"],
            sex_age=d["sex_age"],
            weight_carry=float(d["weight_carry"]),
            jockey_name=d["jockey_name"],
            jockey_id=d["jockey_id"],
            trainer_name=d["trainer_name"],
            trainer_id=d["trainer_id"],
            horse_weight=d.get("horse_weight"),
            morning_odds=float(d["morning_odds"]) if d.get("morning_odds") is not None else None,
            popularity=int(d["popularity"]) if d.get("popularity") is not None else None,
        )


@dataclass
class PastRaceRecord:
    """馬の過去1走分の成績。"""

    race_date: str          # YYYY-MM-DD
    venue: str              # 競馬場
    race_name: str
    surface: str            # 芝/ダート
    distance: int           # 距離(m)
    weather: str            # 天候
    track_condition: str    # 馬場状態（良/稍重/重/不良）
    horse_number: int
    result_order: Optional[int]   # 着順（取消等は None）
    time_str: Optional[str]       # タイム文字列（"1:34.5" 等）
    last_3f: Optional[float]      # 上り3F
    odds: Optional[float]         # 単勝オッズ
    popularity: Optional[int]     # 人気
    weight_carry: Optional[float]
    horse_weight: Optional[str]   # 馬体重（"480(+4)" 等）
    pace: Optional[str]           # ペース情報
    position_at_corners: Optional[str]  # 通過順位（"3-3-2-1" 等）
    race_class: str = ""

    def to_dict(self) -> dict:
        return {
            "race_date": self.race_date,
            "venue": self.venue,
            "race_name": self.race_name,
            "surface": self.surface,
            "distance": self.distance,
            "weather": self.weather,
            "track_condition": self.track_condition,
            "horse_number": self.horse_number,
            "result_order": self.result_order,
            "time_str": self.time_str,
            "last_3f": self.last_3f,
            "odds": self.odds,
            "popularity": self.popularity,
            "weight_carry": self.weight_carry,
            "horse_weight": self.horse_weight,
            "pace": self.pace,
            "position_at_corners": self.position_at_corners,
            "race_class": self.race_class,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PastRaceRecord":
        return cls(
            race_date=d["race_date"],
            venue=d["venue"],
            race_name=d["race_name"],
            surface=d["surface"],
            distance=int(d["distance"]),
            weather=d.get("weather", ""),
            track_condition=d.get("track_condition", ""),
            horse_number=int(d.get("horse_number", 0)),
            result_order=d.get("result_order"),
            time_str=d.get("time_str"),
            last_3f=float(d["last_3f"]) if d.get("last_3f") is not None else None,
            odds=float(d["odds"]) if d.get("odds") is not None else None,
            popularity=int(d["popularity"]) if d.get("popularity") is not None else None,
            weight_carry=float(d["weight_carry"]) if d.get("weight_carry") is not None else None,
            horse_weight=d.get("horse_weight"),
            pace=d.get("pace"),
            position_at_corners=d.get("position_at_corners"),
            race_class=d.get("race_class", ""),
        )


@dataclass
class HorseHistory:
    """馬の過去成績サマリー。"""

    horse_id: str
    horse_name: str
    total_runs: int
    wins: int
    places: int             # 2着回数
    shows: int              # 3着回数
    recent_results: List[PastRaceRecord] = field(default_factory=list)  # 直近5走
    surface_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # 例: {"芝": {"runs": 10, "wins": 3, "places": 2, "shows": 1},
    #       "ダート": {"runs": 5, ...}}
    distance_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # 例: {"1200-1400": {"runs": 5, "wins": 2, ...}, "1600-2000": {...}}
    venue_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # 例: {"中山": {"runs": 3, "wins": 1, ...}}
    running_style: str = ""  # 脚質（逃げ/先行/差し/追込）

    def to_dict(self) -> dict:
        return {
            "horse_id": self.horse_id,
            "horse_name": self.horse_name,
            "total_runs": self.total_runs,
            "wins": self.wins,
            "places": self.places,
            "shows": self.shows,
            "recent_results": [r.to_dict() for r in self.recent_results],
            "surface_stats": self.surface_stats,
            "distance_stats": self.distance_stats,
            "venue_stats": self.venue_stats,
            "running_style": self.running_style,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HorseHistory":
        return cls(
            horse_id=d["horse_id"],
            horse_name=d["horse_name"],
            total_runs=int(d["total_runs"]),
            wins=int(d["wins"]),
            places=int(d["places"]),
            shows=int(d["shows"]),
            recent_results=[PastRaceRecord.from_dict(r) for r in d.get("recent_results", [])],
            surface_stats=d.get("surface_stats", {}),
            distance_stats=d.get("distance_stats", {}),
            venue_stats=d.get("venue_stats", {}),
            running_style=d.get("running_style", ""),
        )


@dataclass
class JockeyStats:
    """騎手成績サマリー。"""

    jockey_id: str
    jockey_name: str
    year_runs: int = 0
    year_wins: int = 0
    year_win_rate: float = 0.0
    year_place_rate: float = 0.0    # 連対率
    year_show_rate: float = 0.0     # 複勝率
    venue_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # 例: {"中山": {"runs": 50, "win_rate": 0.12, "show_rate": 0.30}}

    def to_dict(self) -> dict:
        return {
            "jockey_id": self.jockey_id,
            "jockey_name": self.jockey_name,
            "year_runs": self.year_runs,
            "year_wins": self.year_wins,
            "year_win_rate": self.year_win_rate,
            "year_place_rate": self.year_place_rate,
            "year_show_rate": self.year_show_rate,
            "venue_stats": self.venue_stats,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "JockeyStats":
        return cls(
            jockey_id=d["jockey_id"],
            jockey_name=d["jockey_name"],
            year_runs=int(d.get("year_runs", 0)),
            year_wins=int(d.get("year_wins", 0)),
            year_win_rate=float(d.get("year_win_rate", 0.0)),
            year_place_rate=float(d.get("year_place_rate", 0.0)),
            year_show_rate=float(d.get("year_show_rate", 0.0)),
            venue_stats=d.get("venue_stats", {}),
        )


@dataclass
class TrainerStats:
    """調教師成績サマリー。"""

    trainer_id: str
    trainer_name: str
    year_runs: int = 0
    year_wins: int = 0
    year_win_rate: float = 0.0
    year_show_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "trainer_id": self.trainer_id,
            "trainer_name": self.trainer_name,
            "year_runs": self.year_runs,
            "year_wins": self.year_wins,
            "year_win_rate": self.year_win_rate,
            "year_show_rate": self.year_show_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TrainerStats":
        return cls(
            trainer_id=d["trainer_id"],
            trainer_name=d["trainer_name"],
            year_runs=int(d.get("year_runs", 0)),
            year_wins=int(d.get("year_wins", 0)),
            year_win_rate=float(d.get("year_win_rate", 0.0)),
            year_show_rate=float(d.get("year_show_rate", 0.0)),
        )


@dataclass
class OddsData:
    """全券種のオッズデータ。"""

    race_id: str
    win_odds: Dict[int, float] = field(default_factory=dict)
    # 馬番 -> 単勝オッズ
    place_odds: Dict[int, Tuple[float, float]] = field(default_factory=dict)
    # 馬番 -> 複勝オッズ (min, max)
    quinella_odds: Dict[str, float] = field(default_factory=dict)
    # "1-2" -> 馬連オッズ
    exacta_odds: Dict[str, float] = field(default_factory=dict)
    # "1>2" -> 馬単オッズ
    bracket_quinella_odds: Dict[str, float] = field(default_factory=dict)
    # "1-2" -> 枠連オッズ
    wide_odds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    # "1-2" -> ワイドオッズ (min, max)
    trio_odds: Dict[str, float] = field(default_factory=dict)
    # "1-2-3" -> 三連複オッズ
    trifecta_odds: Dict[str, float] = field(default_factory=dict)
    # "1>2>3" -> 三連単オッズ
    timestamp: str = ""     # 取得時刻 (ISO format)

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "win_odds": {str(k): v for k, v in self.win_odds.items()},
            "place_odds": {str(k): list(v) for k, v in self.place_odds.items()},
            "quinella_odds": self.quinella_odds,
            "exacta_odds": self.exacta_odds,
            "bracket_quinella_odds": self.bracket_quinella_odds,
            "wide_odds": {k: list(v) for k, v in self.wide_odds.items()},
            "trio_odds": self.trio_odds,
            "trifecta_odds": self.trifecta_odds,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OddsData":
        return cls(
            race_id=d["race_id"],
            win_odds={int(k): float(v) for k, v in d.get("win_odds", {}).items()},
            place_odds={int(k): tuple(v) for k, v in d.get("place_odds", {}).items()},
            quinella_odds=d.get("quinella_odds", {}),
            exacta_odds=d.get("exacta_odds", {}),
            bracket_quinella_odds=d.get("bracket_quinella_odds", {}),
            wide_odds={k: tuple(v) for k, v in d.get("wide_odds", {}).items()},
            trio_odds=d.get("trio_odds", {}),
            trifecta_odds=d.get("trifecta_odds", {}),
            timestamp=d.get("timestamp", ""),
        )


@dataclass
class UpcomingRaceWithEntries:
    """未来レース1件の全データ。"""

    race_id: str
    race_name: str
    race_date: str          # YYYY-MM-DD
    venue: str
    surface: str
    distance: int
    race_class: str
    age_condition: str
    number_of_entries: int
    entries: List[UpcomingHorseEntry] = field(default_factory=list)
    horse_histories: Dict[str, HorseHistory] = field(default_factory=dict)
    # horse_id -> HorseHistory
    jockey_stats: Dict[str, JockeyStats] = field(default_factory=dict)
    # jockey_id -> JockeyStats
    trainer_stats: Dict[str, TrainerStats] = field(default_factory=dict)
    # trainer_id -> TrainerStats
    odds: Optional[OddsData] = None
    entry_status: str = ""  # "confirmed" / "partial" / "unconfirmed" / "not_available"
    entry_validation_issues: List[dict] = field(default_factory=list)  # 検証問題リスト

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "race_name": self.race_name,
            "race_date": self.race_date,
            "venue": self.venue,
            "surface": self.surface,
            "distance": self.distance,
            "race_class": self.race_class,
            "age_condition": self.age_condition,
            "number_of_entries": self.number_of_entries,
            "entries": [e.to_dict() for e in self.entries],
            "horse_histories": {k: v.to_dict() for k, v in self.horse_histories.items()},
            "jockey_stats": {k: v.to_dict() for k, v in self.jockey_stats.items()},
            "trainer_stats": {k: v.to_dict() for k, v in self.trainer_stats.items()},
            "odds": self.odds.to_dict() if self.odds else None,
            "entry_status": self.entry_status,
            "entry_validation_issues": self.entry_validation_issues,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UpcomingRaceWithEntries":
        return cls(
            race_id=d["race_id"],
            race_name=d.get("race_name", ""),
            race_date=d["race_date"],
            venue=d["venue"],
            surface=d["surface"],
            distance=int(d["distance"]),
            race_class=d["race_class"],
            age_condition=d.get("age_condition", ""),
            number_of_entries=int(d.get("number_of_entries", 0)),
            entries=[UpcomingHorseEntry.from_dict(e) for e in d.get("entries", [])],
            horse_histories={k: HorseHistory.from_dict(v) for k, v in d.get("horse_histories", {}).items()},
            jockey_stats={k: JockeyStats.from_dict(v) for k, v in d.get("jockey_stats", {}).items()},
            trainer_stats={k: TrainerStats.from_dict(v) for k, v in d.get("trainer_stats", {}).items()},
            odds=OddsData.from_dict(d["odds"]) if d.get("odds") else None,
            entry_status=d.get("entry_status", ""),
            entry_validation_issues=d.get("entry_validation_issues", []),
        )
