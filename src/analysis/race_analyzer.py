"""
レース分析エンジン。

6軸評価（能力・調子・騎手・展開・血統・厩舎）で出走馬を評価し、
印付け・期待値ギャップ検出まで行う。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging
import re
import statistics

logger = logging.getLogger(__name__)

from data.shutuba_schema import (
    HorseHistory,
    JockeyStats,
    OddsData,
    PastRaceRecord,
    TrainerStats,
    UpcomingHorseEntry,
    UpcomingRaceWithEntries,
)


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# 各軸の重み（合計 1.0）
SCORE_WEIGHTS: Dict[str, float] = {
    "ability": 0.30,
    "condition": 0.15,
    "jockey": 0.15,
    "pace": 0.15,
    "bloodline": 0.15,
    "stable": 0.10,
}

# グレード変換閾値
_GRADE_THRESHOLDS: List[Tuple[int, str]] = [
    (80, "A"),
    (60, "B"),
    (40, "C"),
    (20, "D"),
    (0, "E"),
]

# 距離カテゴリ定義（距離統計キーとのマッチングに使用）
_DISTANCE_CATEGORIES: List[Tuple[range, str]] = [
    (range(1000, 1401), "1200-1400"),
    (range(1401, 1801), "1600-1800"),
    (range(1801, 2201), "1800-2200"),
    (range(2201, 2601), "2200-2600"),
    (range(2601, 4001), "2600-3600"),
]

# 脚質判定用の通過順位閾値
_STYLE_THRESHOLDS = {
    "逃げ": 2,
    "先行": 4,
    "差し": 8,
}


def _raw_to_grade(raw: float) -> str:
    """生スコア (0-100) をグレード (A-E) に変換する。"""
    clamped = max(0.0, min(100.0, raw))
    for threshold, grade in _GRADE_THRESHOLDS:
        if clamped >= threshold:
            return grade
    return "E"


def _parse_time_str(time_str: Optional[str]) -> Optional[float]:
    """タイム文字列 ("1:34.5") を秒数に変換する。"""
    if not time_str:
        return None
    m = re.match(r"(\d+):(\d+)\.(\d+)", time_str.strip())
    if not m:
        return None
    minutes = int(m.group(1))
    seconds = int(m.group(2))
    frac = int(m.group(3))
    return minutes * 60.0 + seconds + frac / 10.0


def _distance_category(distance: int) -> str:
    """距離(m) を統計キー用のカテゴリ文字列に変換する。"""
    for rng, cat in _DISTANCE_CATEGORIES:
        if distance in rng:
            return cat
    # 範囲外の場合は最も近いカテゴリを返す
    if distance < 1000:
        return "1200-1400"
    return "2600-3600"


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """0除算を安全に処理する割り算。"""
    if denominator == 0:
        return default
    return numerator / denominator


def _infer_running_style(history: HorseHistory) -> str:
    """
    過去レースの通過順から脚質を推定する。

    HorseHistory.running_style が設定されていればそのまま返す。
    設定されていなければ直近レースの通過順位から推定する。
    """
    if history.running_style:
        return history.running_style

    if not history.recent_results:
        return "差し"  # デフォルト

    # 各レースの最初のコーナー通過順を集める
    first_positions: List[int] = []
    for rec in history.recent_results:
        if rec.position_at_corners:
            parts = rec.position_at_corners.split("-")
            try:
                first_positions.append(int(parts[0]))
            except (ValueError, IndexError):
                continue

    if not first_positions:
        return "差し"

    avg_pos = statistics.mean(first_positions)
    if avg_pos <= _STYLE_THRESHOLDS["逃げ"]:
        return "逃げ"
    elif avg_pos <= _STYLE_THRESHOLDS["先行"]:
        return "先行"
    elif avg_pos <= _STYLE_THRESHOLDS["差し"]:
        return "差し"
    else:
        return "追込"


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------


@dataclass
class HorseEvaluation:
    """1頭の6軸評価結果。"""

    horse_number: int
    horse_name: str
    ability_score: str      # A-E（能力: 過去成績・タイム・着差）
    condition_score: str    # A-E（調子: 上り3F推移、間隔、前走内容）
    jockey_score: str       # A-E（騎手: リーディング、コース成績、乗替）
    pace_score: str         # A-E（展開: 脚質とペース予想）
    bloodline_score: str    # A-E（血統: コース・距離・馬場適性）
    stable_score: str       # A-E（厩舎: 出走傾向、仕上げ）
    total_index: float      # 総合指数 (0-100)
    strengths: List[str] = field(default_factory=list)   # 強み（日本語）
    weaknesses: List[str] = field(default_factory=list)  # 弱み（日本語）
    mark: str = ""          # 印（◎/○/▲/△/×/無印）

    def to_dict(self) -> dict:
        return {
            "horse_number": self.horse_number,
            "horse_name": self.horse_name,
            "ability_score": self.ability_score,
            "condition_score": self.condition_score,
            "jockey_score": self.jockey_score,
            "pace_score": self.pace_score,
            "bloodline_score": self.bloodline_score,
            "stable_score": self.stable_score,
            "total_index": round(self.total_index, 2),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "mark": self.mark,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HorseEvaluation":
        return cls(
            horse_number=int(d["horse_number"]),
            horse_name=d["horse_name"],
            ability_score=d["ability_score"],
            condition_score=d["condition_score"],
            jockey_score=d["jockey_score"],
            pace_score=d["pace_score"],
            bloodline_score=d["bloodline_score"],
            stable_score=d["stable_score"],
            total_index=float(d["total_index"]),
            strengths=d.get("strengths", []),
            weaknesses=d.get("weaknesses", []),
            mark=d.get("mark", ""),
        )


@dataclass
class RaceAnalysis:
    """1レースの分析結果。"""

    race_id: str
    race_name: str
    venue: str
    surface: str
    distance: int
    race_class: str
    # コース傾向
    favorable_frame: str        # 有利な枠（"内枠有利"/"外枠有利"/"フラット"）
    favorable_style: str        # 有利な脚質（"逃げ先行有利"/"差し追込有利"/"フラット"）
    track_condition_impact: str  # 馬場状態の影響
    # レース診断
    volatility: str             # 波乱度（"堅い"/"上位拮抗"/"波乱含み"/"大波乱"）
    confidence: str             # 自信度 (A-D)
    comment: str                # 見解（短評）
    pace_prediction: str        # 展開予想（"ハイペース"/"ミドルペース"/"スローペース"）
    # 全馬評価
    evaluations: List[HorseEvaluation] = field(default_factory=list)  # 総合指数順にソート
    # 最終結論
    honmei: Optional[HorseEvaluation] = None    # ◎本命
    taikou: Optional[HorseEvaluation] = None    # ○対抗
    tanana: Optional[HorseEvaluation] = None    # ▲単穴
    renka: List[HorseEvaluation] = field(default_factory=list)       # △連下
    keshi: List[HorseEvaluation] = field(default_factory=list)       # ×消し（危険な人気馬）
    # 期待値ギャップ
    value_horses: List[dict] = field(default_factory=list)    # 期待値の高い馬
    danger_popular: List[dict] = field(default_factory=list)  # 危険な人気馬
    # レースTier（PREDICTION_POLICY準拠: 1=重賞フル分析, 2=注目レース詳細, 3=通常基本分析）
    race_tier: int = 3

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "race_name": self.race_name,
            "venue": self.venue,
            "surface": self.surface,
            "distance": self.distance,
            "race_class": self.race_class,
            "favorable_frame": self.favorable_frame,
            "favorable_style": self.favorable_style,
            "track_condition_impact": self.track_condition_impact,
            "volatility": self.volatility,
            "confidence": self.confidence,
            "comment": self.comment,
            "pace_prediction": self.pace_prediction,
            "evaluations": [e.to_dict() for e in self.evaluations],
            "honmei": self.honmei.to_dict() if self.honmei else None,
            "taikou": self.taikou.to_dict() if self.taikou else None,
            "tanana": self.tanana.to_dict() if self.tanana else None,
            "renka": [e.to_dict() for e in self.renka],
            "keshi": [e.to_dict() for e in self.keshi],
            "value_horses": self.value_horses,
            "danger_popular": self.danger_popular,
            "race_tier": self.race_tier,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RaceAnalysis":
        return cls(
            race_id=d["race_id"],
            race_name=d["race_name"],
            venue=d["venue"],
            surface=d["surface"],
            distance=int(d["distance"]),
            race_class=d["race_class"],
            favorable_frame=d["favorable_frame"],
            favorable_style=d["favorable_style"],
            track_condition_impact=d["track_condition_impact"],
            volatility=d["volatility"],
            confidence=d["confidence"],
            comment=d["comment"],
            pace_prediction=d["pace_prediction"],
            evaluations=[HorseEvaluation.from_dict(e) for e in d.get("evaluations", [])],
            honmei=HorseEvaluation.from_dict(d["honmei"]) if d.get("honmei") else None,
            taikou=HorseEvaluation.from_dict(d["taikou"]) if d.get("taikou") else None,
            tanana=HorseEvaluation.from_dict(d["tanana"]) if d.get("tanana") else None,
            renka=[HorseEvaluation.from_dict(e) for e in d.get("renka", [])],
            keshi=[HorseEvaluation.from_dict(e) for e in d.get("keshi", [])],
            value_horses=d.get("value_horses", []),
            danger_popular=d.get("danger_popular", []),
            race_tier=int(d.get("race_tier", 3)),
        )


# ---------------------------------------------------------------------------
# 分析エンジン
# ---------------------------------------------------------------------------


class RaceAnalyzer:
    """
    レース分析エンジン。

    UpcomingRaceWithEntries を受け取り、6軸評価に基づく
    RaceAnalysis を返す。
    """

    def __init__(self) -> None:
        """初期化。重みは定数から取得。"""
        self.weights = SCORE_WEIGHTS.copy()

    # =======================================================================
    # 公開メソッド
    # =======================================================================

    def analyze_race(self, race_data: UpcomingRaceWithEntries) -> RaceAnalysis:
        """
        メインの分析メソッド。

        1. 各馬を6軸で評価
        2. 総合指数を算出
        3. ペース予想・波乱度判定
        4. 印付け・期待値ギャップ検出
        """
        # 出馬表未確定チェック
        if race_data.entry_status in ("unconfirmed", "not_available"):
            logger.warning(
                "出馬表未確定のため分析をスキップ: %s (%s)",
                race_data.race_id,
                race_data.entry_status,
            )
            analysis = self._empty_analysis(race_data)
            analysis.comment = "出馬表が未確定のため分析を行えませんでした。"
            return analysis

        # 一部未確定の場合は警告を付与して分析を実施
        if race_data.entry_status == "partial":
            logger.warning(
                "出馬表一部未確定。警告付きで分析を実施: %s",
                race_data.race_id,
            )

        entries = race_data.entries
        if not entries:
            # 出走馬が0頭の場合は空の分析結果を返す
            return self._empty_analysis(race_data)

        # --- 全馬の戦績・統計を取得 ---
        all_histories: Dict[str, HorseHistory] = race_data.horse_histories
        all_jockey_stats: Dict[str, JockeyStats] = race_data.jockey_stats
        all_trainer_stats: Dict[str, TrainerStats] = race_data.trainer_stats
        odds_data: Optional[OddsData] = race_data.odds

        # --- ペース予想（全馬の脚質から判定） ---
        pace_prediction = self._predict_pace(entries, all_histories)

        # --- 各馬を6軸で評価 ---
        evaluations: List[HorseEvaluation] = []
        for entry in entries:
            history = all_histories.get(entry.horse_id)
            jockey_stat = all_jockey_stats.get(entry.jockey_id)
            trainer_stat = all_trainer_stats.get(entry.trainer_id)

            # 各軸スコア算出
            ability_grade, ability_raw = self._score_ability(entry, history, race_data)
            condition_grade, condition_raw = self._score_condition(entry, history)
            jockey_grade, jockey_raw = self._score_jockey(
                entry, jockey_stat, race_data
            )
            pace_grade, pace_raw = self._score_pace(
                entry, history, entries, all_histories, pace_prediction
            )
            bloodline_grade, bloodline_raw = self._score_bloodline(
                entry, history, race_data
            )
            stable_grade, stable_raw = self._score_stable(entry, trainer_stat)

            # 総合指数
            raw_scores = {
                "ability": ability_raw,
                "condition": condition_raw,
                "jockey": jockey_raw,
                "pace": pace_raw,
                "bloodline": bloodline_raw,
                "stable": stable_raw,
            }
            total_index = self._calculate_total_index(raw_scores)

            # 強み・弱みを判定
            strengths, weaknesses = self._evaluate_strengths_weaknesses(
                ability_grade, condition_grade, jockey_grade,
                pace_grade, bloodline_grade, stable_grade,
                entry, history, race_data,
            )

            ev = HorseEvaluation(
                horse_number=entry.horse_number,
                horse_name=entry.horse_name,
                ability_score=ability_grade,
                condition_score=condition_grade,
                jockey_score=jockey_grade,
                pace_score=pace_grade,
                bloodline_score=bloodline_grade,
                stable_score=stable_grade,
                total_index=total_index,
                strengths=strengths,
                weaknesses=weaknesses,
            )
            evaluations.append(ev)

        # --- 総合指数でソート（降順） ---
        evaluations.sort(key=lambda e: e.total_index, reverse=True)

        # --- 印付け ---
        evaluations = self._assign_marks(evaluations)

        # --- 波乱度判定 ---
        volatility = self._determine_volatility(evaluations, odds_data)

        # --- 期待値ギャップ ---
        value_horses, danger_popular = self._find_value_gaps(evaluations, odds_data)

        # --- コース傾向 ---
        favorable_frame = self._assess_frame_advantage(race_data)
        favorable_style = self._assess_style_advantage(pace_prediction)
        track_condition_impact = self._assess_track_condition(race_data)

        # --- 自信度・コメント生成 ---
        confidence = self._assess_confidence(evaluations, volatility)
        comment = self._generate_comment(
            evaluations, pace_prediction, volatility, race_data
        )

        # --- 印から最終結論を設定 ---
        honmei = next((e for e in evaluations if e.mark == "◎"), None)
        taikou = next((e for e in evaluations if e.mark == "○"), None)
        tanana = next((e for e in evaluations if e.mark == "▲"), None)
        renka = [e for e in evaluations if e.mark == "△"]
        keshi = [e for e in evaluations if e.mark == "×"]

        # --- レースTier分類（PREDICTION_POLICY準拠） ---
        race_tier = self._classify_race_tier(
            race_data, volatility, confidence, value_horses
        )

        return RaceAnalysis(
            race_id=race_data.race_id,
            race_name=race_data.race_name,
            venue=race_data.venue,
            surface=race_data.surface,
            distance=race_data.distance,
            race_class=race_data.race_class,
            favorable_frame=favorable_frame,
            favorable_style=favorable_style,
            track_condition_impact=track_condition_impact,
            volatility=volatility,
            confidence=confidence,
            comment=comment,
            pace_prediction=pace_prediction,
            evaluations=evaluations,
            honmei=honmei,
            taikou=taikou,
            tanana=tanana,
            renka=renka,
            keshi=keshi,
            value_horses=value_horses,
            danger_popular=danger_popular,
            race_tier=race_tier,
        )

    # =======================================================================
    # 各軸スコア算出（プライベートメソッド）
    # =======================================================================

    def _score_ability(
        self,
        entry: UpcomingHorseEntry,
        history: Optional[HorseHistory],
        race_data: UpcomingRaceWithEntries,
    ) -> Tuple[str, float]:
        """
        能力軸スコア。

        評価要素:
        - 勝率・連対率・複勝率
        - 直近レースのタイム（距離補正済み）
        - 着差（着順の安定感）
        - 同条件（コース・距離）での成績
        """
        if not history or history.total_runs == 0:
            # 戦績なし（新馬等）→ 中間評価
            return "C", 50.0

        score = 0.0

        # --- 1. 全体成績ベーススコア (最大30点) ---
        win_rate = _safe_div(history.wins, history.total_runs)
        place_rate = _safe_div(history.wins + history.places, history.total_runs)
        show_rate = _safe_div(
            history.wins + history.places + history.shows, history.total_runs
        )
        # 勝率を重視した配点
        score += win_rate * 15.0   # 最大15点
        score += place_rate * 10.0  # 最大10点
        score += show_rate * 5.0    # 最大5点

        # --- 2. 直近レースのタイムスコア (最大25点) ---
        time_scores: List[float] = []
        for rec in history.recent_results[:5]:
            if rec.result_order is None:
                continue
            # 着順ベースのスコア（1着=10, 2着=8, 3着=6, ...）
            order_score = max(0.0, 11.0 - rec.result_order) if rec.result_order <= 10 else 0.0
            time_scores.append(order_score)
        if time_scores:
            # 直近の成績ほど重みを大きくする（減衰係数）
            weighted_sum = 0.0
            weight_total = 0.0
            for i, ts in enumerate(time_scores):
                w = 1.0 / (1.0 + i * 0.3)  # 直近=1.0, 2走前≈0.77, ...
                weighted_sum += ts * w
                weight_total += w
            avg_order_score = _safe_div(weighted_sum, weight_total)
            score += avg_order_score * 2.5  # 最大25点

        # --- 3. 同条件成績 (最大25点) ---
        # コース（芝/ダート）適性
        surface_key = race_data.surface
        surface_stat = history.surface_stats.get(surface_key, {})
        surface_runs = surface_stat.get("runs", 0)
        if surface_runs > 0:
            surface_win_rate = _safe_div(surface_stat.get("wins", 0), surface_runs)
            surface_show_rate = _safe_div(
                surface_stat.get("wins", 0) + surface_stat.get("places", 0)
                + surface_stat.get("shows", 0),
                surface_runs,
            )
            score += surface_win_rate * 8.0
            score += surface_show_rate * 4.0
        else:
            # 未経験 → 中間
            score += 4.0

        # 距離適性
        dist_cat = _distance_category(race_data.distance)
        dist_stat = history.distance_stats.get(dist_cat, {})
        dist_runs = dist_stat.get("runs", 0)
        if dist_runs > 0:
            dist_win_rate = _safe_div(dist_stat.get("wins", 0), dist_runs)
            dist_show_rate = _safe_div(
                dist_stat.get("wins", 0) + dist_stat.get("places", 0)
                + dist_stat.get("shows", 0),
                dist_runs,
            )
            score += dist_win_rate * 8.0
            score += dist_show_rate * 5.0
        else:
            score += 4.0

        # --- 4. 上り3Fの実力 (最大20点) ---
        last_3f_values: List[float] = []
        for rec in history.recent_results[:5]:
            if rec.last_3f is not None and rec.last_3f > 0:
                last_3f_values.append(rec.last_3f)
        if last_3f_values:
            avg_last_3f = statistics.mean(last_3f_values)
            # 33秒台 → 高得点、36秒以上 → 低得点
            # 33.0 → 20点, 36.0+ → 0点 の線形マッピング
            three_f_score = max(0.0, min(20.0, (36.5 - avg_last_3f) / 3.5 * 20.0))
            score += three_f_score

        # 100点満点に正規化
        raw = min(100.0, max(0.0, score))
        return _raw_to_grade(raw), raw

    def _score_condition(
        self,
        entry: UpcomingHorseEntry,
        history: Optional[HorseHistory],
    ) -> Tuple[str, float]:
        """
        調子軸スコア。

        評価要素:
        - 上り3F推移（直近3走の改善/悪化）
        - レース間隔（適切な間隔かどうか）
        - 前走着順と内容
        - 馬体重変動
        """
        if not history or not history.recent_results:
            return "C", 50.0

        score = 0.0
        recent = history.recent_results

        # --- 1. 上り3F推移 (最大30点) ---
        last_3f_series: List[float] = []
        for rec in recent[:3]:
            if rec.last_3f is not None and rec.last_3f > 0:
                last_3f_series.append(rec.last_3f)

        if len(last_3f_series) >= 2:
            # 改善傾向（上り3Fが小さくなっている）ほど高評価
            # 直近 - 2走前 の差を見る（マイナス=改善）
            improvement = last_3f_series[-1] - last_3f_series[0]
            # -1.0秒改善 → 30点、+1.0秒悪化 → 0点
            trend_score = max(0.0, min(30.0, (0.5 - improvement) / 1.0 * 15.0 + 15.0))
            score += trend_score
        elif len(last_3f_series) == 1:
            # 1走分しかない場合は中間
            score += 15.0
        else:
            score += 10.0

        # --- 2. レース間隔 (最大25点) ---
        if len(recent) >= 1 and recent[0].race_date:
            try:
                from datetime import datetime

                last_race_date = datetime.strptime(recent[0].race_date, "%Y-%m-%d")
                # 現在日を race_date から推定（race_data が無いので固定的に計算）
                # 間隔は日数で判定
                # ここでは最新レースの日付を基準に相対的に評価
                # 理想的な間隔: 中2-4週（14-28日）
                if len(recent) >= 2 and recent[1].race_date:
                    prev_date = datetime.strptime(recent[1].race_date, "%Y-%m-%d")
                    interval_days = (last_race_date - prev_date).days
                else:
                    interval_days = 21  # デフォルト（中3週）

                if 14 <= interval_days <= 35:
                    # 理想的な間隔
                    score += 25.0
                elif 7 <= interval_days < 14:
                    # やや詰まっている
                    score += 18.0
                elif 35 < interval_days <= 60:
                    # やや空いている
                    score += 18.0
                elif 60 < interval_days <= 120:
                    # 休み明け
                    score += 12.0
                elif interval_days > 120:
                    # 長期休養明け
                    score += 5.0
                else:
                    # 連闘（7日未満）
                    score += 10.0
            except (ValueError, TypeError):
                score += 12.0
        else:
            score += 12.0

        # --- 3. 前走内容 (最大25点) ---
        if recent[0].result_order is not None:
            last_order = recent[0].result_order
            if last_order == 1:
                score += 25.0
            elif last_order == 2:
                score += 22.0
            elif last_order == 3:
                score += 19.0
            elif last_order <= 5:
                score += 14.0
            elif last_order <= 8:
                score += 8.0
            else:
                # ただし上り最速なら加点
                if recent[0].last_3f is not None and recent[0].last_3f < 34.0:
                    score += 10.0
                else:
                    score += 3.0
        else:
            # 取消等
            score += 5.0

        # --- 4. 馬体重変動 (最大20点) ---
        weight_changes = self._parse_weight_changes(recent[:3])
        if weight_changes:
            # 安定した体重変動（-4〜+4kg）が理想的
            last_change = weight_changes[0]
            if last_change is not None:
                abs_change = abs(last_change)
                if abs_change <= 4:
                    score += 20.0
                elif abs_change <= 8:
                    score += 14.0
                elif abs_change <= 14:
                    score += 8.0
                else:
                    # 大幅な増減は不安要素
                    score += 3.0
            else:
                score += 10.0
        else:
            score += 10.0

        raw = min(100.0, max(0.0, score))
        return _raw_to_grade(raw), raw

    def _score_jockey(
        self,
        entry: UpcomingHorseEntry,
        jockey_stats: Optional[JockeyStats],
        race_data: UpcomingRaceWithEntries,
    ) -> Tuple[str, float]:
        """
        騎手軸スコア。

        評価要素:
        - リーディング成績（年間勝率・複勝率）
        - コース別成績
        - 乗り替わりの影響
        """
        if not jockey_stats:
            # 騎手データなし → 中間評価
            return "C", 50.0

        score = 0.0

        # --- 1. 年間成績ベース (最大40点) ---
        # 勝率 20% → 40点、0% → 0点
        win_component = min(40.0, jockey_stats.year_win_rate * 200.0)
        score += win_component

        # --- 2. 複勝率ベース (最大20点) ---
        # 複勝率 40% → 20点、0% → 0点
        show_component = min(20.0, jockey_stats.year_show_rate * 50.0)
        score += show_component

        # --- 3. コース別成績 (最大25点) ---
        venue = race_data.venue
        venue_stat = jockey_stats.venue_stats.get(venue, {})
        venue_runs = venue_stat.get("runs", 0)
        if venue_runs >= 5:
            # 十分なサンプルサイズがある場合
            venue_win_rate = venue_stat.get("win_rate", 0.0)
            venue_show_rate = venue_stat.get("show_rate", 0.0)
            score += min(15.0, venue_win_rate * 100.0)
            score += min(10.0, venue_show_rate * 25.0)
        elif venue_runs > 0:
            # サンプル少ないが参考にする
            venue_show_rate = venue_stat.get("show_rate", 0.0)
            score += venue_show_rate * 15.0
        else:
            # コース未経験 → 年間成績の半分を適用
            score += min(12.5, jockey_stats.year_show_rate * 25.0)

        # --- 4. 騎乗数による信頼度補正 (最大15点) ---
        # 年間騎乗数が多いほど安定感がある
        if jockey_stats.year_runs >= 200:
            score += 15.0
        elif jockey_stats.year_runs >= 100:
            score += 12.0
        elif jockey_stats.year_runs >= 50:
            score += 8.0
        elif jockey_stats.year_runs >= 20:
            score += 5.0
        else:
            score += 2.0

        raw = min(100.0, max(0.0, score))
        return _raw_to_grade(raw), raw

    def _score_pace(
        self,
        entry: UpcomingHorseEntry,
        history: Optional[HorseHistory],
        all_entries: List[UpcomingHorseEntry],
        all_histories: Dict[str, HorseHistory],
        pace_prediction: str,
    ) -> Tuple[str, float]:
        """
        展開軸スコア。

        評価要素:
        - 予想ペースと脚質の相性
        - 枠番と脚質の組み合わせ
        - 逃げ馬・先行馬の数
        """
        if not history:
            return "C", 50.0

        score = 0.0
        style = _infer_running_style(history)
        num_entries = len(all_entries)

        # --- 1. ペースと脚質の相性 (最大40点) ---
        pace_style_matrix = {
            "ハイペース": {"逃げ": 15, "先行": 25, "差し": 40, "追込": 35},
            "ミドルペース": {"逃げ": 30, "先行": 35, "差し": 30, "追込": 25},
            "スローペース": {"逃げ": 40, "先行": 35, "差し": 20, "追込": 10},
        }
        matrix = pace_style_matrix.get(pace_prediction, pace_style_matrix["ミドルペース"])
        score += matrix.get(style, 25)

        # --- 2. 枠番と脚質の組み合わせ (最大25点) ---
        frame = entry.frame_number
        total_frames = max(1, num_entries // 2) if num_entries > 2 else 1
        is_inner = frame <= max(1, total_frames // 2)

        if style in ("逃げ", "先行"):
            # 先行勢は内枠有利
            if is_inner:
                score += 25.0
            else:
                score += 15.0
        elif style == "差し":
            # 差し馬は中枠が理想的
            if not is_inner and frame <= total_frames:
                score += 22.0
            else:
                score += 18.0
        else:
            # 追込は外枠でも問題なし
            score += 20.0

        # --- 3. 同脚質の競合数による補正 (最大20点) ---
        same_style_count = 0
        for other_entry in all_entries:
            if other_entry.horse_number == entry.horse_number:
                continue
            other_history = all_histories.get(other_entry.horse_id)
            if other_history:
                other_style = _infer_running_style(other_history)
                if other_style == style:
                    same_style_count += 1

        if style in ("逃げ", "先行"):
            # 逃げ・先行馬が少ないほど有利
            if same_style_count == 0:
                score += 20.0  # 単騎逃げ/先行なしで楽
            elif same_style_count <= 2:
                score += 15.0
            elif same_style_count <= 4:
                score += 10.0
            else:
                score += 5.0
        else:
            # 差し・追込は逃げ先行が多いほど有利（ハイペースになりやすい）
            front_runners = 0
            for other_entry in all_entries:
                other_history = all_histories.get(other_entry.horse_id)
                if other_history:
                    other_style = _infer_running_style(other_history)
                    if other_style in ("逃げ", "先行"):
                        front_runners += 1
            if front_runners >= 4:
                score += 20.0
            elif front_runners >= 2:
                score += 14.0
            else:
                score += 8.0

        # --- 4. 直近の位置取り安定性 (最大15点) ---
        positions: List[int] = []
        for rec in (history.recent_results or [])[:5]:
            if rec.position_at_corners:
                parts = rec.position_at_corners.split("-")
                try:
                    positions.append(int(parts[0]))
                except (ValueError, IndexError):
                    continue
        if len(positions) >= 2:
            pos_std = statistics.stdev(positions) if len(positions) > 1 else 0.0
            # 安定している（標準偏差が小さい）ほど高評価
            stability_score = max(0.0, 15.0 - pos_std * 3.0)
            score += stability_score
        else:
            score += 7.0

        raw = min(100.0, max(0.0, score))
        return _raw_to_grade(raw), raw

    def _score_bloodline(
        self,
        entry: UpcomingHorseEntry,
        history: Optional[HorseHistory],
        race_data: UpcomingRaceWithEntries,
    ) -> Tuple[str, float]:
        """
        血統軸スコア。

        評価要素:
        - コース（芝/ダート）適性（過去成績から推定）
        - 距離適性（過去成績から推定）
        - 会場適性（過去成績から推定）

        注: 実際の血統DB（父・母父等）を持たないため、
        過去の条件別成績をプロキシとして使用する。
        """
        if not history or history.total_runs == 0:
            # 実績なし → 中間評価
            return "C", 50.0

        score = 0.0

        # --- 1. コース適性 (最大35点) ---
        surface = race_data.surface
        surface_stat = history.surface_stats.get(surface, {})
        surface_runs = surface_stat.get("runs", 0)
        if surface_runs >= 3:
            surface_show = _safe_div(
                surface_stat.get("wins", 0) + surface_stat.get("places", 0)
                + surface_stat.get("shows", 0),
                surface_runs,
            )
            score += min(35.0, surface_show * 70.0)
        elif surface_runs > 0:
            # 少ないサンプルだが参考にする
            surface_show = _safe_div(
                surface_stat.get("wins", 0) + surface_stat.get("places", 0)
                + surface_stat.get("shows", 0),
                surface_runs,
            )
            score += min(25.0, surface_show * 50.0)
        else:
            # 未経験のコース → やや不安だが未知数ということで中間寄り
            score += 12.0

        # --- 2. 距離適性 (最大35点) ---
        dist_cat = _distance_category(race_data.distance)
        dist_stat = history.distance_stats.get(dist_cat, {})
        dist_runs = dist_stat.get("runs", 0)
        if dist_runs >= 3:
            dist_show = _safe_div(
                dist_stat.get("wins", 0) + dist_stat.get("places", 0)
                + dist_stat.get("shows", 0),
                dist_runs,
            )
            score += min(35.0, dist_show * 70.0)
        elif dist_runs > 0:
            dist_show = _safe_div(
                dist_stat.get("wins", 0) + dist_stat.get("places", 0)
                + dist_stat.get("shows", 0),
                dist_runs,
            )
            score += min(25.0, dist_show * 50.0)
        else:
            # 近い距離カテゴリで代替評価
            fallback_score = self._fallback_distance_score(history, race_data.distance)
            score += fallback_score

        # --- 3. 会場適性 (最大30点) ---
        venue = race_data.venue
        venue_stat = history.venue_stats.get(venue, {})
        venue_runs = venue_stat.get("runs", 0)
        if venue_runs >= 2:
            venue_show = _safe_div(
                venue_stat.get("wins", 0) + venue_stat.get("places", 0)
                + venue_stat.get("shows", 0),
                venue_runs,
            )
            score += min(30.0, venue_show * 60.0)
        elif venue_runs > 0:
            venue_show = _safe_div(
                venue_stat.get("wins", 0) + venue_stat.get("places", 0)
                + venue_stat.get("shows", 0),
                venue_runs,
            )
            score += min(20.0, venue_show * 40.0)
        else:
            # 未経験の会場 → 全体成績を参考
            overall_show = _safe_div(
                history.wins + history.places + history.shows, history.total_runs
            )
            score += min(15.0, overall_show * 30.0)

        raw = min(100.0, max(0.0, score))
        return _raw_to_grade(raw), raw

    def _score_stable(
        self,
        entry: UpcomingHorseEntry,
        trainer_stats: Optional[TrainerStats],
    ) -> Tuple[str, float]:
        """
        厩舎軸スコア。

        評価要素:
        - 調教師の年間勝率・複勝率
        - 出走数（アクティブさ）
        """
        if not trainer_stats:
            return "C", 50.0

        score = 0.0

        # --- 1. 年間勝率 (最大40点) ---
        # 勝率15% → 40点、0% → 0点
        score += min(40.0, trainer_stats.year_win_rate * 267.0)

        # --- 2. 年間複勝率 (最大30点) ---
        # 複勝率 35% → 30点、0% → 0点
        score += min(30.0, trainer_stats.year_show_rate * 86.0)

        # --- 3. 出走数（活動量・仕上げ力の指標） (最大30点) ---
        if trainer_stats.year_runs >= 100:
            score += 30.0
        elif trainer_stats.year_runs >= 60:
            score += 24.0
        elif trainer_stats.year_runs >= 30:
            score += 18.0
        elif trainer_stats.year_runs >= 10:
            score += 10.0
        else:
            score += 5.0

        raw = min(100.0, max(0.0, score))
        return _raw_to_grade(raw), raw

    # =======================================================================
    # 総合指数算出
    # =======================================================================

    def _calculate_total_index(self, scores: Dict[str, float]) -> float:
        """
        6軸の生スコアから重み付き平均で総合指数を算出する。

        各スコアは0-100の範囲で、重みは SCORE_WEIGHTS に従う。
        """
        total = 0.0
        for axis, raw in scores.items():
            weight = self.weights.get(axis, 0.0)
            total += raw * weight
        return round(min(100.0, max(0.0, total)), 2)

    # =======================================================================
    # ペース予想
    # =======================================================================

    def _predict_pace(
        self,
        entries: List[UpcomingHorseEntry],
        all_histories: Dict[str, HorseHistory],
    ) -> str:
        """
        出走馬全体の脚質分布からレースのペースを予想する。

        逃げ・先行馬が多ければハイペース、
        差し・追込が多ければスローペース。
        """
        style_counts = {"逃げ": 0, "先行": 0, "差し": 0, "追込": 0}
        total = 0

        for entry in entries:
            history = all_histories.get(entry.horse_id)
            if history:
                style = _infer_running_style(history)
                style_counts[style] = style_counts.get(style, 0) + 1
                total += 1

        if total == 0:
            return "ミドルペース"

        front_ratio = _safe_div(
            style_counts["逃げ"] + style_counts["先行"], total
        )
        escape_count = style_counts["逃げ"]

        # 逃げ馬が3頭以上、または前残り比率が60%以上 → ハイペース
        if escape_count >= 3 or front_ratio >= 0.6:
            return "ハイペース"
        # 逃げ馬が0頭、または前残り比率が25%以下 → スローペース
        elif escape_count == 0 or front_ratio <= 0.25:
            return "スローペース"
        else:
            return "ミドルペース"

    # =======================================================================
    # 波乱度判定
    # =======================================================================

    def _determine_volatility(
        self,
        evaluations: List[HorseEvaluation],
        odds_data: Optional[OddsData],
    ) -> str:
        """
        上位馬のスコア分布とオッズから波乱度を判定する。

        - 1位と2位の差が大きく、1番人気と一致 → 堅い
        - 上位が拮抗 → 上位拮抗
        - 指数上位とオッズ人気が乖離 → 波乱含み / 大波乱
        """
        if len(evaluations) < 2:
            return "堅い"

        top = evaluations[0].total_index
        second = evaluations[1].total_index
        third = evaluations[2].total_index if len(evaluations) >= 3 else 0.0

        # 上位間の差
        gap_1_2 = top - second
        gap_1_3 = top - third

        # オッズとの乖離チェック
        odds_mismatch = False
        if odds_data and odds_data.win_odds:
            # 指数1位の馬番を取得
            top_horse_num = evaluations[0].horse_number
            # オッズで1番人気の馬番を取得
            if odds_data.win_odds:
                popular_horse_num = min(
                    odds_data.win_odds, key=odds_data.win_odds.get
                )
                if top_horse_num != popular_horse_num:
                    odds_mismatch = True

        # 判定ロジック
        if gap_1_2 >= 10.0 and not odds_mismatch:
            return "堅い"
        elif gap_1_2 >= 5.0 and gap_1_3 >= 8.0:
            if odds_mismatch:
                return "波乱含み"
            return "堅い"
        elif gap_1_2 < 3.0:
            if odds_mismatch:
                return "大波乱"
            return "上位拮抗"
        else:
            if odds_mismatch:
                return "波乱含み"
            return "上位拮抗"

    # =======================================================================
    # 印付け
    # =======================================================================

    def _assign_marks(
        self, evaluations: List[HorseEvaluation]
    ) -> List[HorseEvaluation]:
        """
        総合指数順に印を割り当てる。

        ◎ = 1位（本命）
        ○ = 2位（対抗）
        ▲ = 3位（単穴）
        △ = 4-6位（連下） ※指数が上位と大差なければ
        × = 人気だが指数が低い馬（危険な人気馬）
        無印 = その他
        """
        if not evaluations:
            return evaluations

        # 指数が僅差（3点以内）のグループを考慮
        top_index = evaluations[0].total_index

        for i, ev in enumerate(evaluations):
            if i == 0:
                ev.mark = "◎"
            elif i == 1:
                ev.mark = "○"
            elif i == 2:
                ev.mark = "▲"
            elif i <= 5:
                # 上位との差が15点以内なら△
                if top_index - ev.total_index <= 15.0:
                    ev.mark = "△"
                else:
                    ev.mark = ""
            else:
                ev.mark = ""

        return evaluations

    # =======================================================================
    # 期待値ギャップ検出
    # =======================================================================

    def _find_value_gaps(
        self,
        evaluations: List[HorseEvaluation],
        odds_data: Optional[OddsData],
    ) -> Tuple[List[dict], List[dict]]:
        """
        指数とオッズの乖離から期待値の高い馬・危険な人気馬を検出する。

        value_horses: 指数は高いがオッズが甘い（過小評価されている）馬
        danger_popular: 指数は低いがオッズが低い（過大評価されている）馬
        """
        value_horses: List[dict] = []
        danger_popular: List[dict] = []

        if not odds_data or not odds_data.win_odds:
            return value_horses, danger_popular

        # 指数順位を記録
        index_rank: Dict[int, int] = {}
        for rank, ev in enumerate(evaluations, 1):
            index_rank[ev.horse_number] = rank

        # オッズ順位を算出（低いオッズ = 人気）
        sorted_odds = sorted(odds_data.win_odds.items(), key=lambda x: x[1])
        odds_rank: Dict[int, int] = {}
        for rank, (horse_num, _) in enumerate(sorted_odds, 1):
            odds_rank[horse_num] = rank

        for ev in evaluations:
            hn = ev.horse_number
            i_rank = index_rank.get(hn, len(evaluations))
            o_rank = odds_rank.get(hn, len(evaluations))
            odds_val = odds_data.win_odds.get(hn, 0.0)

            # 指数上位なのにオッズが甘い（3ランク以上のギャップ）
            if i_rank <= 5 and o_rank - i_rank >= 3:
                value_horses.append({
                    "horse_number": hn,
                    "reason": (
                        f"指数{i_rank}位だがオッズ{o_rank}番人気（{odds_val:.1f}倍）"
                        f"で過小評価。{ev.horse_name}の実力は上位。"
                    ),
                })

            # オッズ人気だが指数が低い（3ランク以上のギャップ）
            if o_rank <= 3 and i_rank - o_rank >= 3:
                # ×印も付ける
                ev.mark = "×"
                danger_popular.append({
                    "horse_number": hn,
                    "reason": (
                        f"オッズ{o_rank}番人気（{odds_val:.1f}倍）だが"
                        f"指数{i_rank}位。{ev.horse_name}は過大評価の可能性。"
                    ),
                })

        return value_horses, danger_popular

    # =======================================================================
    # レースTier分類（PREDICTION_POLICY準拠）
    # =======================================================================

    _GRADED_KEYWORDS = ("G1", "G2", "G3", "GI", "GII", "GIII", "重賞", "リステッド", "Listed")
    _NOTABLE_KEYWORDS = ("ステークス", "特別", "賞")

    def _classify_race_tier(
        self,
        race_data: UpcomingRaceWithEntries,
        volatility: str,
        confidence: str,
        value_horses: List[dict],
    ) -> int:
        """
        レースをTierに分類する（PREDICTION_POLICY.md 準拠）。

        Tier 1: 重賞レース（G1〜G3、リステッド） → フル分析
        Tier 2: 注目レース（妙味のある平場） → 詳細分析
        Tier 3: 通常レース → 基本分析

        Returns:
            1, 2, or 3
        """
        race_name = race_data.race_name or ""
        race_class = race_data.race_class or ""
        combined = f"{race_name}{race_class}"

        # --- Tier 1: 重賞 ---
        if any(kw in combined for kw in self._GRADED_KEYWORDS):
            return 1

        # --- Tier 2 判定（いずれかに該当すれば昇格） ---
        # 条件1: 特別戦（○○ステークス等の名前付きレース）
        if any(kw in race_name for kw in self._NOTABLE_KEYWORDS):
            return 2

        # 条件2: 波乱度が「波乱含み」以上
        if volatility in ("波乱含み", "大波乱"):
            return 2

        # 条件3: 自信度A（データ的に読みやすく的中を取りに行ける）
        if confidence == "A":
            return 2

        # 条件4: 期待値ギャップが大きい（実力と人気の乖離が顕著な馬がいる）
        if value_horses:
            return 2

        # --- Tier 3: 通常レース ---
        return 3

    # =======================================================================
    # ヘルパーメソッド
    # =======================================================================

    def _parse_weight_changes(
        self, records: List[PastRaceRecord]
    ) -> List[Optional[int]]:
        """
        直近レースの馬体重変動を抽出する。

        horse_weight フォーマット: "480(+4)" → +4
        """
        changes: List[Optional[int]] = []
        for rec in records:
            if not rec.horse_weight:
                changes.append(None)
                continue
            m = re.search(r"\(([+-]?\d+)\)", rec.horse_weight)
            if m:
                changes.append(int(m.group(1)))
            else:
                changes.append(None)
        return changes

    def _fallback_distance_score(
        self, history: HorseHistory, target_distance: int
    ) -> float:
        """
        目標距離のカテゴリに成績がない場合、近い距離カテゴリから推定する。
        """
        target_cat = _distance_category(target_distance)
        best_score = 12.0  # デフォルト中間値

        for cat, stat in history.distance_stats.items():
            runs = stat.get("runs", 0)
            if runs == 0:
                continue

            # カテゴリ間の距離を算出
            cat_distances = {
                "1200-1400": 1300,
                "1600-1800": 1700,
                "1800-2200": 2000,
                "2200-2600": 2400,
                "2600-3600": 3100,
            }
            target_mid = cat_distances.get(target_cat, target_distance)
            cat_mid = cat_distances.get(cat, 1700)
            distance_diff = abs(target_mid - cat_mid)

            # 距離差が近いカテゴリの成績を参考にする（減衰あり）
            if distance_diff <= 400:
                show_rate = _safe_div(
                    stat.get("wins", 0) + stat.get("places", 0)
                    + stat.get("shows", 0),
                    runs,
                )
                # 距離差による減衰
                decay = 1.0 - (distance_diff / 800.0)
                candidate = min(25.0, show_rate * 50.0 * decay)
                best_score = max(best_score, candidate)

        return best_score

    def _evaluate_strengths_weaknesses(
        self,
        ability: str,
        condition: str,
        jockey: str,
        pace: str,
        bloodline: str,
        stable: str,
        entry: UpcomingHorseEntry,
        history: Optional[HorseHistory],
        race_data: UpcomingRaceWithEntries,
    ) -> Tuple[List[str], List[str]]:
        """各軸の評価から強み・弱みリストを生成する。"""
        strengths: List[str] = []
        weaknesses: List[str] = []

        # 能力軸
        if ability in ("A", "B"):
            strengths.append("過去成績が優秀")
        elif ability in ("D", "E"):
            weaknesses.append("実績が乏しい")

        # 調子軸
        if condition in ("A", "B"):
            strengths.append("好調を維持")
        elif condition in ("D", "E"):
            weaknesses.append("調子に不安")

        # 騎手軸
        if jockey in ("A",):
            strengths.append(f"トップジョッキー（{entry.jockey_name}）")
        elif jockey in ("B",):
            strengths.append(f"安定感のある騎手（{entry.jockey_name}）")
        elif jockey in ("D", "E"):
            weaknesses.append("騎手の成績が不安")

        # 展開軸
        if pace in ("A", "B"):
            strengths.append("展開が向きそう")
        elif pace in ("D", "E"):
            weaknesses.append("展開が厳しい")

        # 血統（条件適性）軸
        if bloodline in ("A",):
            strengths.append("コース・距離適性抜群")
        elif bloodline in ("B",):
            strengths.append("条件適性あり")
        elif bloodline in ("D", "E"):
            weaknesses.append("条件適性に疑問")

        # 厩舎軸
        if stable in ("A",):
            strengths.append("名門厩舎の仕上げ")
        elif stable in ("D", "E"):
            weaknesses.append("厩舎の勝負度が低い")

        # 枠番に関する追加コメント
        if history:
            style = _infer_running_style(history)
            frame = entry.frame_number
            num_entries = race_data.number_of_entries
            is_inner = frame <= max(1, num_entries // 4)
            is_outer = frame >= max(1, num_entries * 3 // 4)

            if style in ("逃げ", "先行") and is_inner:
                strengths.append("先行脚質で内枠好位置")
            elif style in ("逃げ", "先行") and is_outer:
                weaknesses.append("先行脚質だが外枠")
            elif style in ("差し", "追込") and is_outer and race_data.distance >= 2000:
                strengths.append("長距離で外枠の差し・追込")

        return strengths, weaknesses

    def _assess_frame_advantage(self, race_data: UpcomingRaceWithEntries) -> str:
        """
        コース条件から枠順有利不利を判定する。

        短距離・小回りコースは内枠有利、
        長距離・大箱コースはフラット傾向。
        """
        distance = race_data.distance
        venue = race_data.venue

        # 小回りコース（中山・福島・小倉・札幌・函館）
        small_tracks = {"中山", "福島", "小倉", "札幌", "函館"}
        is_small_track = venue in small_tracks

        if distance <= 1400:
            # 短距離は内枠有利
            return "内枠有利"
        elif distance <= 1800 and is_small_track:
            # 小回りコースのマイル前後は内枠有利
            return "内枠有利"
        elif distance >= 2400:
            # 長距離はフラット
            return "フラット"
        else:
            if is_small_track:
                return "内枠有利"
            return "フラット"

    def _assess_style_advantage(self, pace_prediction: str) -> str:
        """ペース予想から有利な脚質を判定する。"""
        if pace_prediction == "スローペース":
            return "逃げ先行有利"
        elif pace_prediction == "ハイペース":
            return "差し追込有利"
        else:
            return "フラット"

    def _assess_track_condition(self, race_data: UpcomingRaceWithEntries) -> str:
        """馬場状態の影響を評価する。"""
        surface = race_data.surface

        # 実際の馬場状態は UpcomingRaceWithEntries に含まれていないため、
        # コース種別に基づく一般的なコメントを返す
        if surface == "芝":
            return "芝コース。良馬場なら実力通りの決着が期待できる"
        elif surface == "ダート":
            return "ダートコース。パワー型の馬に注目"
        else:
            return "コース状態の詳細情報なし"

    def _assess_confidence(
        self, evaluations: List[HorseEvaluation], volatility: str
    ) -> str:
        """
        分析の自信度を判定する。

        A: 自信度高（堅い + 明確な差）
        B: やや自信あり
        C: 自信薄（上位拮抗）
        D: 判断困難
        """
        if not evaluations:
            return "D"

        if len(evaluations) < 3:
            return "C"

        top_gap = evaluations[0].total_index - evaluations[1].total_index

        if volatility == "堅い" and top_gap >= 8.0:
            return "A"
        elif volatility == "堅い" or top_gap >= 5.0:
            return "B"
        elif volatility in ("上位拮抗", "波乱含み"):
            return "C"
        else:
            return "D"

    def _generate_comment(
        self,
        evaluations: List[HorseEvaluation],
        pace_prediction: str,
        volatility: str,
        race_data: UpcomingRaceWithEntries,
    ) -> str:
        """レース全体の見解を短評として生成する。"""
        if not evaluations:
            return "出走馬の情報が不足しているため分析不可。"

        top = evaluations[0]
        parts: List[str] = []

        # 本命馬のコメント
        parts.append(f"{top.horse_name}が指数トップ")

        # ペースコメント
        if pace_prediction == "ハイペース":
            parts.append("ハイペース予想で差し馬台頭の可能性")
        elif pace_prediction == "スローペース":
            parts.append("スロー予想で前残りに警戒")
        else:
            parts.append("ミドルペースで実力勝負の展開")

        # 波乱度コメント
        if volatility == "大波乱":
            parts.append("混戦模様で波乱の余地あり")
        elif volatility == "波乱含み":
            parts.append("人気馬に死角あり注意")
        elif volatility == "上位拮抗":
            parts.append("上位は僅差で予断を許さない")
        else:
            parts.append("実力上位が順当に力を発揮する展開か")

        return "。".join(parts) + "。"

    def _empty_analysis(self, race_data: UpcomingRaceWithEntries) -> RaceAnalysis:
        """出走馬がいない場合の空の分析結果を返す。"""
        return RaceAnalysis(
            race_id=race_data.race_id,
            race_name=race_data.race_name,
            venue=race_data.venue,
            surface=race_data.surface,
            distance=race_data.distance,
            race_class=race_data.race_class,
            favorable_frame="フラット",
            favorable_style="フラット",
            track_condition_impact="情報なし",
            volatility="堅い",
            confidence="D",
            comment="出走馬の情報がありません。",
            pace_prediction="ミドルペース",
            evaluations=[],
            honmei=None,
            taikou=None,
            tanana=None,
            renka=[],
            keshi=[],
            value_horses=[],
            danger_popular=[],
        )
