"""
シミュレーション実行のインターフェース（MVP）。
シミュレーション可能ロジックのみ過去5年バックテスト可能。
券種: 単勝・複勝、100円換算、発走直前最終オッズ固定。
"""
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from models.logic_type import LogicType, classify_logic
from models.custom_variable import CustomVariable
from models.simulation_spec import BetType, BET_UNIT_JPY, SIMULATION_OUTPUTS
from data.schema import Race, HorseEntry
from data import storage


# ── シミュレーション可否判定 ──

def check_simulatable(logic_record: dict) -> Tuple[bool, str]:
    """
    ロジックレコード（logics.json の1要素）からシミュレーション可否を判定。
    戻り値: (可否, 不可理由の文字列。可の場合は空文字)
    """
    # カスタム変数は2つの形式がある:
    # 1. logic_store 形式: "custom_vars": {"variables": [{"name": ..., ...}, ...]}
    # 2. 旧形式: "custom_variables": [{"name": ..., ...}, ...]
    cv_data = logic_record.get("custom_vars")
    custom_vars_raw = []
    if isinstance(cv_data, dict):
        custom_vars_raw = cv_data.get("variables", [])
    elif isinstance(cv_data, list):
        custom_vars_raw = cv_data
    else:
        # 旧キー名のフォールバック
        cv_legacy = logic_record.get("custom_variables", [])
        if isinstance(cv_legacy, list):
            custom_vars_raw = cv_legacy

    custom_vars = []
    for cv in custom_vars_raw:
        if isinstance(cv, dict) and cv.get("name"):
            custom_vars.append(
                CustomVariable(name=cv["name"], var_type=None)
            )

    # MVP では Scope/Must/Prefer-Avoid はすべて事前定義の選択肢を使うため
    # 自由入力テキストや外部データは現状存在しない
    is_selection_only = True
    uses_internal_data_only = True

    logic_type = classify_logic(
        is_selection_only=is_selection_only,
        uses_internal_data_only=uses_internal_data_only,
        custom_variables=custom_vars,
    )

    if logic_type == LogicType.SIMULATION_INCAPABLE:
        reasons = []
        if custom_vars:
            reasons.append("カスタム変数を含むため")
        if not is_selection_only:
            reasons.append("自由入力項目を含むため")
        if not uses_internal_data_only:
            reasons.append("外部データを使用しているため")
        reason = "、".join(reasons) if reasons else "シミュレーション不可条件に該当"
        return False, reason

    return True, ""


def get_logic_type_info(logic_record: dict) -> Dict[str, Any]:
    """
    ロジックのシミュレーション可否情報を辞書で返す（UI表示用）。
    戻り値: {
        "can_simulate": bool,
        "logic_type": str（"シミュレーション可能" or "シミュレーション不可"）,
        "reason": str（不可理由。可の場合は空文字）,
        "description": str（UIに表示する説明文）,
    }
    """
    can_sim, reason = check_simulatable(logic_record)
    if can_sim:
        return {
            "can_simulate": True,
            "logic_type": LogicType.SIMULATION_CAPABLE.value,
            "reason": "",
            "description": "過去5年のバックテストが実行可能です。",
        }
    else:
        return {
            "can_simulate": False,
            "logic_type": LogicType.SIMULATION_INCAPABLE.value,
            "reason": reason,
            "description": f"バックテストは実行できません（{reason}）。フォワード成績のみ記録可能です。",
        }


# ── Scope マッチング ──

# 旧距離カテゴリ → 距離(m) 範囲の変換（後方互換用）
_DISTANCE_RANGES = {
    "短距離": (0, 1400),
    "マイル": (1401, 1800),
    "中距離": (1801, 2400),
    "長距離": (2401, 99999),
}


def _race_matches_scope(race: Race, scope: dict) -> bool:
    """レースが Scope 条件に合致するか判定する。"""
    if scope.get("venues") and race.venue not in scope["venues"]:
        return False
    if scope.get("surface") and race.surface not in scope["surface"]:
        return False
    if scope.get("race_class") and race.race_class not in scope["race_class"]:
        return False
    if scope.get("age_condition") and race.age_condition not in scope["age_condition"]:
        return False
    # 距離: distance_min / distance_max による範囲比較
    d_min = scope.get("distance_min")
    d_max = scope.get("distance_max")
    if d_min is not None and d_max is not None:
        if not (int(d_min) <= race.distance <= int(d_max)):
            return False
    elif scope.get("distances"):
        # 旧形式（カテゴリリスト）の後方互換
        matched = False
        for cat in scope["distances"]:
            lo, hi = _DISTANCE_RANGES.get(cat, (0, 0))
            if lo <= race.distance <= hi:
                matched = True
                break
        if not matched:
            return False
    return True


# ── Must フィルタ ──

# バックテスト未対応のカテゴリ（データに存在しない項目）
_UNSUPPORTED_CATEGORIES = {"血統指標"}


def _get_entry_value(entry: HorseEntry, category: str) -> Optional[Any]:
    """Must/Prefer-Avoid のカテゴリ名から馬の実データ値を返す。"""
    mapping = {
        "前走着順": entry.previous_order,
        "前走4角位置": entry.previous_position_4c,
        "前走距離": entry.previous_distance,
        "斤量": entry.weight,
        "枠番／馬番": entry.horse_number,
        "最終オッズ帯": entry.final_odds,
        "馬の性別": entry.horse_sex,
        "前走間隔（日数）": entry.days_since_last_race,
    }
    return mapping.get(category)


def _compare(actual, operator: str, target_str: str) -> bool:
    """演算子で比較する。actual が None の場合は不一致。"""
    if actual is None:
        return False
    try:
        # 数値同士はfloatに統一して比較（int("3.5")のエラーを防ぐ）
        if isinstance(actual, (int, float)):
            target = float(target_str)
            actual = float(actual)
        else:
            target = type(actual)(target_str)
    except (ValueError, TypeError):
        return False
    ops = {
        "eq": actual == target,
        "le": actual <= target,
        "ge": actual >= target,
        "lt": actual < target,
        "gt": actual > target,
        "in": str(target) in str(actual),
    }
    return ops.get(operator, False)


def _entry_passes_must(entry: HorseEntry, must: Optional[dict]) -> bool:
    """Must 条件を通過するか。Must が未設定なら全馬通過。"""
    if not must or not must.get("blocks"):
        return True
    # ブロック間はAND: すべてのブロックを満たす必要がある
    for block in must["blocks"]:
        conditions = block.get("conditions", [])
        if not conditions:
            continue
        # 未対応カテゴリのみのブロックはスキップ（条件通過扱い）
        supported_conds = [c for c in conditions if c.get("category", "") not in _UNSUPPORTED_CATEGORIES]
        if not supported_conds:
            continue
        # 同一ブロック内はOR: いずれかの条件を満たせばOK
        block_pass = False
        for cond in supported_conds:
            cat = cond.get("category", "")
            op = cond.get("operator", "eq")
            val = str(cond.get("value", ""))
            actual = _get_entry_value(entry, cat)
            if _compare(actual, op, val):
                block_pass = True
                break
        if not block_pass:
            return False
    return True


# ── Prefer/Avoid ランキング ──

def _rank_entries(entries: List[HorseEntry], prefer_avoid: Optional[dict]) -> List[HorseEntry]:
    """
    Prefer/Avoid でレキシコグラフィック方式の順位付け。
    Prefer: 条件を満たす馬が上位（優先順位1→2→... の順で段階比較）
    Avoid: 条件を満たす馬は最下位寄り
    """
    if not prefer_avoid:
        return entries

    prefer_list = prefer_avoid.get("prefer", [])
    avoid_list = prefer_avoid.get("avoid", [])

    def score_key(entry: HorseEntry):
        # Avoid に該当 → (1, ...) で下位に
        avoid_flag = 0
        for a in avoid_list:
            criteria = a.get("criteria", {})
            cat = criteria.get("category", "")
            op = criteria.get("operator", "eq")
            val = str(criteria.get("value", ""))
            actual = _get_entry_value(entry, cat)
            if _compare(actual, op, val):
                avoid_flag = 1
                break

        # Prefer をレキシコグラフィック方式で評価（条件を満たす=0、満たさない=1）
        prefer_scores = []
        for p in sorted(prefer_list, key=lambda x: x.get("order", 999)):
            criteria = p.get("criteria", {})
            cat = criteria.get("category", "")
            op = criteria.get("operator", "eq")
            val = str(criteria.get("value", ""))
            actual = _get_entry_value(entry, cat)
            prefer_scores.append(0 if _compare(actual, op, val) else 1)

        return (avoid_flag, *prefer_scores)

    return sorted(entries, key=score_key)


# ── バックテストエンジン ──

def run_backtest(
    logic_record: dict,
    bet_type: BetType,
    data_years: int = 5,
    base_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    バックテスト実行（シミュレーション可能ロジックのみ）。
    保存済みレースデータを使い、ロジックの Scope/Must/Prefer-Avoid で
    過去レースを再検証して成績を算出する。
    シミュレーション不可ロジックの場合は ValueError を送出する。
    """
    # シミュレーション可否のガード
    can_sim, reason = check_simulatable(logic_record)
    if not can_sim:
        raise ValueError(f"シミュレーション不可ロジックです: {reason}")

    scope = logic_record.get("scope", {})
    must = logic_record.get("must")
    prefer_avoid = logic_record.get("prefer_avoid")

    # 過去5年分のレースを読み込み
    all_races = storage.load_races(base_path)
    cutoff = date.today() - timedelta(days=data_years * 365)
    races = [r for r in all_races if r.date >= cutoff]

    # Scope でフィルタ
    matched_races = [r for r in races if _race_matches_scope(r, scope)]

    # レースごとにシミュレーション
    trials = 0
    hits = 0
    total_payout = 0.0
    total_bet = 0.0
    total_win_amount = 0.0  # 的中時の純利益合計
    total_loss_amount = 0.0  # 不的中時の損失合計
    yearly_results: Dict[int, Dict[str, Any]] = {}
    cumulative_profit = 0.0
    max_drawdown = 0.0
    peak_profit = 0.0
    current_losing_streak = 0
    max_losing_streak = 0
    current_winning_streak = 0
    max_winning_streak = 0

    for race in sorted(matched_races, key=lambda r: r.date):
        entries = storage.load_entries(race.race_id, base_path)
        if not entries:
            continue

        # Must フィルタ
        passed = [e for e in entries if _entry_passes_must(e, must)]
        if not passed:
            continue

        # Prefer/Avoid で順位付け → 1位の馬に賭ける
        ranked = _rank_entries(passed, prefer_avoid)
        pick = ranked[0]

        # 結果判定
        if pick.result_order is None or pick.final_odds is None:
            continue

        trials += 1
        total_bet += BET_UNIT_JPY
        year = race.date.year

        if year not in yearly_results:
            yearly_results[year] = {"試行回数": 0, "的中数": 0, "投資額": 0.0, "回収額": 0.0}
        yearly_results[year]["試行回数"] += 1
        yearly_results[year]["投資額"] += BET_UNIT_JPY

        # 的中判定
        is_hit = False
        if bet_type == BetType.WIN:
            # 単勝: 1着
            is_hit = pick.result_order == 1
        elif bet_type == BetType.PLACE:
            # 複勝: 3着以内（8頭以上の場合。7頭以下は2着以内が正式だが MVP は3着以内で統一）
            is_hit = pick.result_order <= 3

        if is_hit:
            hits += 1
            # 払戻: 100円 × オッズ（複勝オッズは単勝の約1/2.6で近似）
            if bet_type == BetType.WIN:
                payout = BET_UNIT_JPY * pick.final_odds
            else:
                payout = BET_UNIT_JPY * (pick.final_odds / 2.6)
            total_payout += payout
            total_win_amount += (payout - BET_UNIT_JPY)
            yearly_results[year]["的中数"] += 1
            yearly_results[year]["回収額"] += payout
            current_losing_streak = 0
            current_winning_streak += 1
            max_winning_streak = max(max_winning_streak, current_winning_streak)
        else:
            total_loss_amount += BET_UNIT_JPY
            current_losing_streak += 1
            max_losing_streak = max(max_losing_streak, current_losing_streak)
            current_winning_streak = 0

        # ドローダウン計算
        cumulative_profit = total_payout - total_bet
        if cumulative_profit > peak_profit:
            peak_profit = cumulative_profit
        drawdown = peak_profit - cumulative_profit
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # 結果集計
    recovery_rate = (total_payout / total_bet * 100) if total_bet > 0 else 0.0
    hit_rate = (hits / trials * 100) if trials > 0 else 0.0

    # 年別推移
    yearly_list = []
    for y in sorted(yearly_results.keys()):
        yr = yearly_results[y]
        yr_recovery = (yr["回収額"] / yr["投資額"] * 100) if yr["投資額"] > 0 else 0.0
        yr_hit_rate = (yr["的中数"] / yr["試行回数"] * 100) if yr["試行回数"] > 0 else 0.0
        yearly_list.append({
            "年": y,
            "試行回数": yr["試行回数"],
            "的中率": round(yr_hit_rate, 1),
            "回収率": round(yr_recovery, 1),
        })

    # 追加指標
    avg_profit = (total_payout - total_bet) / trials if trials > 0 else 0.0
    if total_loss_amount > 0:
        profit_factor = total_win_amount / total_loss_amount
    elif total_win_amount > 0:
        profit_factor = float('inf')
    else:
        profit_factor = 0.0
    if trials < 50:
        confidence = "low"
    elif trials < 200:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "試行回数": trials,
        "回収率": round(recovery_rate, 1),
        "的中率": round(hit_rate, 1),
        "年別推移": yearly_list,
        "最大ドローダウン": round(max_drawdown, 0),
        "最大連敗数": max_losing_streak,
        "最大連勝数": max_winning_streak,
        "平均利益": round(avg_profit, 1),
        "Profit Factor": profit_factor if profit_factor == float('inf') else round(profit_factor, 2),
        "信頼度": confidence,
    }


def get_simulation_output_schema() -> List[str]:
    """シミュレーション出力項目（定義固定）。"""
    return list(SIMULATION_OUTPUTS)
