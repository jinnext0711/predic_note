"""
予想画面 - レース情報入力 → ロジック選択 → 出走馬入力 → 予想結果。
"""
import streamlit as st
from pages.styles import inject_custom_css, show_help


def _apply_fetched_to_widgets():
    """フェッチしたレース情報をStep 1のウィジェットに反映する。"""
    from constants.scope_options import VENUES, SURFACE_TYPES, RACE_CLASSES, AGE_CONDITIONS

    data = st.session_state.get("pred_fetched_data")
    if not data:
        st.session_state.pop("_pred_apply_fetch", None)
        return

    meta = data.get("race_meta", {})

    venue = meta.get("venue", "")
    if venue in VENUES:
        st.session_state["pred_venue"] = venue

    surface = meta.get("surface", "")
    if surface in SURFACE_TYPES:
        st.session_state["pred_surface"] = surface

    distance = meta.get("distance", 0)
    if distance:
        st.session_state["pred_distance"] = int(distance)

    race_class = meta.get("race_class", "")
    if race_class in RACE_CLASSES:
        st.session_state["pred_class"] = race_class

    age_condition = meta.get("age_condition", "")
    if age_condition in AGE_CONDITIONS:
        st.session_state["pred_age"] = age_condition

    st.session_state.pop("_pred_apply_fetch", None)


def _do_fetch(race_id: str):
    """netkeibaからレースデータを取得してセッションに保存する。"""
    from data.shutuba_fetcher import ShutubaFetcher
    from data.upcoming_storage import load_upcoming_race, save_upcoming_race

    # キャッシュ確認
    cached = load_upcoming_race(race_id)
    if cached:
        _store_fetched_data(cached)
        st.session_state["_pred_apply_fetch"] = True
        st.rerun()
        return

    fetcher = ShutubaFetcher(interval=2.0)

    with st.spinner("出馬表を取得中..."):
        race_meta, entries = fetcher.fetch_shutuba(race_id)

    if not entries:
        st.error("出馬表の取得に失敗しました。レースIDを確認してください。")
        return

    with st.spinner("オッズを取得中..."):
        win_odds = fetcher.fetch_win_odds(race_id)

    from data.shutuba_schema import UpcomingRaceWithEntries, OddsData
    from datetime import datetime

    odds_data = None
    if win_odds:
        odds_data = OddsData(
            race_id=race_id,
            win_odds=win_odds,
            timestamp=datetime.now().isoformat(),
        )

    race_data = UpcomingRaceWithEntries(
        race_id=race_id,
        race_name=race_meta.get("race_name", ""),
        race_date=race_meta.get("race_date", ""),
        venue=race_meta.get("venue", ""),
        surface=race_meta.get("surface", ""),
        distance=race_meta.get("distance", 0),
        race_class=race_meta.get("race_class", ""),
        age_condition=race_meta.get("age_condition", ""),
        number_of_entries=len(entries),
        entries=entries,
        odds=odds_data,
    )

    save_upcoming_race(race_data)
    _store_fetched_data(race_data)
    st.session_state["_pred_apply_fetch"] = True
    st.rerun()


def _do_fetch_histories(race_id: str):
    """出走馬の前走データ（戦績）を取得してセッションに更新する。"""
    from data.shutuba_fetcher import ShutubaFetcher
    from data.upcoming_storage import load_upcoming_race, save_upcoming_race

    cached = load_upcoming_race(race_id)
    if not cached:
        st.error("先にレースデータを取得してください。")
        return

    if cached.horse_histories:
        _store_fetched_data(cached)
        st.rerun()
        return

    fetcher = ShutubaFetcher(interval=2.0)
    total = len(cached.entries)
    progress = st.progress(0, text="前走データを取得中...")

    for i, entry in enumerate(cached.entries):
        progress.progress(
            (i + 1) / total,
            text=f"前走データを取得中... {entry.horse_name} ({i+1}/{total})",
        )
        history = fetcher.fetch_horse_history(entry.horse_id, entry.horse_name)
        if history:
            cached.horse_histories[entry.horse_id] = history

    progress.empty()

    save_upcoming_race(cached)
    _store_fetched_data(cached)
    st.rerun()


def _store_fetched_data(race_data):
    """UpcomingRaceWithEntries からセッション用のデータに変換して保存する。"""
    meta = {
        "race_name": race_data.race_name,
        "venue": race_data.venue,
        "surface": race_data.surface,
        "distance": race_data.distance,
        "race_class": race_data.race_class,
        "age_condition": race_data.age_condition,
    }

    horses = []
    for entry in race_data.entries:
        # オッズ: win_odds > morning_odds
        odds = None
        if race_data.odds and entry.horse_number in race_data.odds.win_odds:
            odds = race_data.odds.win_odds[entry.horse_number]
        elif entry.morning_odds is not None:
            odds = entry.morning_odds

        # 前走データ（horse_histories から取得）
        prev_order = None
        prev_distance = None
        prev_4c = None
        history = race_data.horse_histories.get(entry.horse_id)
        if history and history.recent_results:
            last_race = history.recent_results[0]
            prev_order = last_race.result_order
            prev_distance = last_race.distance
            # 4角位置: "3-3-2-1" → 最後の数字
            if last_race.position_at_corners:
                parts = last_race.position_at_corners.strip().split("-")
                try:
                    prev_4c = int(parts[-1])
                except (ValueError, IndexError):
                    pass

        horses.append({
            "horse_number": entry.horse_number,
            "horse_name": entry.horse_name,
            "final_odds": odds,
            "weight": entry.weight_carry,
            "previous_order": prev_order,
            "previous_distance": prev_distance,
            "previous_position_4c": prev_4c,
            "jockey_name": entry.jockey_name,
        })

    st.session_state["pred_fetched_data"] = {
        "race_meta": meta,
        "horses": horses,
        "race_id": race_data.race_id,
        "has_histories": bool(race_data.horse_histories),
    }
    st.session_state["pred_fetched_horses"] = horses


def render():
    inject_custom_css()

    username = st.session_state.get("auth_user", "")
    st.header("予想")
    show_help(
        "対象レースの条件を入力すると、一致するロジックを自動で探します。"
        "ロジックを選んで出走馬情報を入力すれば、推奨馬を算出します。"
    )

    # ステップ管理
    if "pred_step" not in st.session_state:
        st.session_state.pred_step = 1

    # 取り込みデータの適用（リラン時に実行）
    if st.session_state.get("_pred_apply_fetch"):
        _apply_fetched_to_widgets()

    # === netkeibaからデータ取り込み ===
    with st.container(border=True):
        st.markdown("**netkeibaからレースデータを取り込む**")
        col_id, col_btn = st.columns([3, 1])
        with col_id:
            race_id_input = st.text_input(
                "レースID（12桁）",
                placeholder="例: 202506010101",
                key="pred_race_id_input",
            )
        with col_btn:
            st.write("")
            if st.button("取得", key="pred_fetch_btn"):
                if race_id_input.strip():
                    _do_fetch(race_id_input.strip())
                else:
                    st.warning("レースIDを入力してください。")

        fetched_info = st.session_state.get("pred_fetched_data")
        if fetched_info:
            meta = fetched_info.get("race_meta", {})
            horses_list = fetched_info.get("horses", [])
            st.success(
                f"取得済み: {meta.get('race_name', '')} "
                f"{meta.get('venue', '')} {meta.get('surface', '')}{meta.get('distance', '')}m "
                f"({len(horses_list)}頭)"
            )
            if st.button("取り込みデータをクリア", key="pred_clear_fetch"):
                st.session_state.pop("pred_fetched_data", None)
                st.session_state.pop("pred_fetched_horses", None)
                st.rerun()

    # === ステップ1: レース情報入力 ===
    st.subheader("Step 1: レース情報")
    from constants.scope_options import VENUES, SURFACE_TYPES, RACE_CLASSES, AGE_CONDITIONS

    col1, col2, col3 = st.columns(3)
    with col1:
        venue = st.selectbox("競馬場", VENUES, key="pred_venue")
        distance = st.number_input("距離（m）", min_value=800, max_value=3600, value=1600, step=200, key="pred_distance")
    with col2:
        surface = st.radio("芝/ダート", SURFACE_TYPES, key="pred_surface", horizontal=True)
        race_class = st.selectbox("クラス", RACE_CLASSES, key="pred_class")
    with col3:
        age_condition = st.selectbox("年齢条件", AGE_CONDITIONS, key="pred_age")

    race_info = {
        "venue": venue,
        "distance": distance,
        "surface": surface,
        "race_class": race_class,
        "age_condition": age_condition,
    }

    # 購入済みロジックの対象条件をヒント表示
    from auth_store import get_purchased_logics
    import logic_store as _ls
    _purchased_keys = get_purchased_logics(username)
    if _purchased_keys:
        with st.expander("購入済みロジックの対象条件", expanded=False):
            for _pk in _purchased_keys:
                _p_owner = _pk.split("::", 1)[0] if "::" in _pk else ""
                _p_name = _pk.split("::", 1)[1] if "::" in _pk else _pk
                _p_rec = _ls.get_logic(_p_name, owner=_p_owner)
                if _p_rec and _p_rec.get("scope"):
                    _s = _p_rec["scope"]
                    _parts = []
                    if _s.get("venues"):
                        _parts.append("場: " + "・".join(_s["venues"]))
                    if _s.get("surface"):
                        _parts.append("/".join(_s["surface"]))
                    _d_min = _s.get("distance_min")
                    _d_max = _s.get("distance_max")
                    if _d_min is not None and _d_max is not None:
                        _parts.append(f"{_d_min}-{_d_max}m")
                    if _s.get("race_class"):
                        _parts.append("・".join(_s["race_class"]))
                    if _s.get("age_condition"):
                        _parts.append("・".join(_s["age_condition"]))
                    st.write(f"**{_p_name}** ({_p_owner}): {' | '.join(_parts)}")

    if st.button("ロジックを検索", type="primary", key="pred_search"):
        st.session_state.pred_race_info = race_info
        st.session_state.pred_step = 2

    if st.session_state.pred_step < 2:
        return

    # === ステップ2: マッチするロジック一覧 ===
    st.divider()
    st.subheader("Step 2: マッチするロジック")

    from prediction import find_matching_logics
    race_info_saved = st.session_state.get("pred_race_info", race_info)
    matching_logics = find_matching_logics(race_info_saved, username)

    if not matching_logics:
        st.warning("条件に一致するロジックが見つかりません。レース条件を変更するか、新しいロジックを作成してください。")
        return

    # ロジック表示（成績付き）
    st.write(f"**{len(matching_logics)}件** のロジックが見つかりました。")

    logic_display = []
    for rec in matching_logics:
        name = rec.get("name", "")
        owner = rec.get("owner", "")
        is_own = rec.get("_is_own", False)
        label = f"{name} ({'自分' if is_own else owner})"
        logic_display.append(label)

    selected_idx = st.selectbox(
        "使用するロジックを選択",
        range(len(matching_logics)),
        format_func=lambda i: logic_display[i],
        key="pred_logic_select",
    )
    selected_logic = matching_logics[selected_idx]
    is_own_logic = selected_logic.get("_is_own", False)

    # ロジック情報表示（ブラックボックス保護）
    with st.container(border=True):
        col_name, col_bt = st.columns([1, 2])
        with col_name:
            st.markdown(f"**{selected_logic.get('name', '')}**")
            st.caption(f"作者: {selected_logic.get('owner', '')}")
            if is_own_logic:
                st.caption("（自分のロジック）")
            else:
                st.caption("（購入済みロジック - 詳細は非公開）")

        with col_bt:
            # バックテスト成績があれば表示（マーケットプレイス情報から）
            import marketplace_store
            logic_key = selected_logic.get("_logic_key", "")
            listing = marketplace_store.get_listing(logic_key)
            if listing:
                c1, c2 = st.columns(2)
                with c1:
                    bt_win = listing.get("backtest_win", {})
                    if bt_win:
                        st.markdown("**単勝**")
                        st.write(f"的中率: {bt_win.get('的中率', '-')}% / 回収率: {bt_win.get('回収率', '-')}%")
                with c2:
                    bt_place = listing.get("backtest_place", {})
                    if bt_place:
                        st.markdown("**複勝**")
                        st.write(f"的中率: {bt_place.get('的中率', '-')}% / 回収率: {bt_place.get('回収率', '-')}%")

        # 自分のロジックの場合はScope/Must/Prefer詳細表示
        if is_own_logic:
            with st.expander("ロジック詳細を見る"):
                _show_logic_detail(selected_logic)

    if st.button("出走馬を入力する", key="pred_to_step3"):
        st.session_state.pred_selected_logic = selected_logic
        st.session_state.pred_step = 3

    if st.session_state.pred_step < 3:
        return

    # === ステップ3: 出走馬情報 ===
    st.divider()
    st.subheader("Step 3: 出走馬情報")

    selected_logic_saved = st.session_state.get("pred_selected_logic", selected_logic)

    # 必要カテゴリの判定
    from prediction import get_required_categories
    required_cats = get_required_categories(selected_logic_saved)

    if required_cats:
        st.info(f"このロジックでは次の項目が使用されます: {', '.join(required_cats)}")

    fetched_horses = st.session_state.get("pred_fetched_horses")

    if fetched_horses:
        # === 取り込みデータで表示 ===
        needs_prev = any(c in required_cats for c in ["前走着順", "前走距離", "前走4角位置"])
        has_prev = any(h.get("previous_order") is not None for h in fetched_horses)

        if needs_prev and not has_prev:
            st.warning("このロジックは前走データを使用しますが、まだ取得されていません。")
            fetched_data = st.session_state.get("pred_fetched_data", {})
            fetch_race_id = fetched_data.get("race_id", "")
            if fetch_race_id and st.button("前走データを取得", key="pred_fetch_hist"):
                _do_fetch_histories(fetch_race_id)

        import pandas as pd
        display_rows = []
        for h in fetched_horses:
            row = {
                "馬番": h["horse_number"],
                "馬名": h["horse_name"],
                "オッズ": h.get("final_odds") or "未定",
                "斤量": h.get("weight") or "-",
                "騎手": h.get("jockey_name", "-"),
            }
            if needs_prev:
                row["前走着順"] = h.get("previous_order") or "-"
                row["前走距離"] = h.get("previous_distance") or "-"
                row["前走4角"] = h.get("previous_position_4c") or "-"
            display_rows.append(row)

        df = pd.DataFrame(display_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # オッズ未定の馬にデフォルト値を設定
        horses_data = [dict(h) for h in fetched_horses]
        no_odds = [h for h in horses_data if h.get("final_odds") is None]
        if no_odds:
            st.warning(f"{len(no_odds)}頭のオッズが未定です。デフォルト値(10.0)を使用します。")
            for h in horses_data:
                if h.get("final_odds") is None:
                    h["final_odds"] = 10.0

    else:
        # === 手入力 ===
        needs_weight = "斤量" in required_cats
        needs_prev_order = "前走着順" in required_cats
        needs_prev_distance = "前走距離" in required_cats

        num_horses = st.number_input("出走頭数", min_value=2, max_value=18, value=8, key="pred_num_horses")
        st.caption("馬番・馬名・オッズは必須です。その他はロジックに応じて入力してください。")

        horses_data = []
        for i in range(int(num_horses)):
            with st.container(border=True):
                st.markdown(f"**{i + 1}番**")
                cols = st.columns(6)
                with cols[0]:
                    h_number = st.number_input(
                        "馬番", min_value=1, max_value=18, value=i + 1,
                        key=f"pred_hnum_{i}",
                    )
                with cols[1]:
                    h_name = st.text_input("馬名", key=f"pred_hname_{i}")
                with cols[2]:
                    h_odds = st.number_input(
                        "オッズ", min_value=1.0, value=10.0, step=0.1,
                        key=f"pred_hodds_{i}",
                    )
                with cols[3]:
                    h_weight = None
                    if needs_weight:
                        h_weight = st.number_input(
                            "斤量", min_value=48.0, max_value=62.0, value=55.0, step=0.5,
                            key=f"pred_hweight_{i}",
                        )
                with cols[4]:
                    h_prev_order = None
                    if needs_prev_order:
                        h_prev_order = st.number_input(
                            "前走着順", min_value=1, max_value=18, value=5,
                            key=f"pred_hprev_{i}",
                        )
                with cols[5]:
                    h_prev_dist = None
                    if needs_prev_distance:
                        h_prev_dist = st.number_input(
                            "前走距離", min_value=800, max_value=3600, value=1600, step=200,
                            key=f"pred_hpdist_{i}",
                        )

                horses_data.append({
                    "horse_number": h_number,
                    "horse_name": h_name,
                    "final_odds": h_odds,
                    "weight": h_weight,
                    "previous_order": h_prev_order,
                    "previous_distance": h_prev_dist,
                    "previous_position_4c": None,
                })

    bet_type = st.radio("券種", ["単勝", "複勝"], key="pred_bet_type", horizontal=True)

    if st.button("予想を実行", type="primary", key="pred_run"):
        if not fetched_horses:
            # 手入力のバリデーション
            names_filled = all(h["horse_name"].strip() for h in horses_data)
            if not names_filled:
                st.error("すべての馬名を入力してください。")
                return

        st.session_state.pred_horses = horses_data
        st.session_state.pred_bet_type = bet_type
        st.session_state.pred_step = 4

    if st.session_state.pred_step < 4:
        return

    # === ステップ4: 予想結果 ===
    st.divider()
    st.subheader("Step 4: 予想結果")

    horses_saved = st.session_state.get("pred_horses", horses_data)
    bet_type_saved = st.session_state.get("pred_bet_type", bet_type)

    from prediction import build_horse_entry, run_prediction

    # HorseEntryリスト構築
    entries = []
    for h in horses_saved:
        entry = build_horse_entry(
            race_id="prediction",
            horse_number=h["horse_number"],
            horse_name=h["horse_name"],
            final_odds=h["final_odds"],
            weight=h.get("weight"),
            previous_order=h.get("previous_order"),
            previous_distance=h.get("previous_distance"),
            previous_position_4c=h.get("previous_position_4c"),
        )
        entries.append(entry)

    # 予想実行
    pick = run_prediction(selected_logic_saved, entries)

    if pick is None:
        st.warning("条件に合致する馬が見つかりませんでした。Must条件で全馬が除外された可能性があります。")
    else:
        with st.container(border=True):
            st.markdown("### 推奨馬")
            col_result, col_info = st.columns([1, 1])
            with col_result:
                st.markdown(f"## {pick.horse_number}番 {pick.horse_name}")
                st.markdown(f"**券種**: {bet_type_saved}")
                if pick.final_odds:
                    st.write(f"オッズ: {pick.final_odds}")
            with col_info:
                st.markdown(f"**使用ロジック**: {selected_logic_saved.get('name', '')}")
                st.caption(f"作者: {selected_logic_saved.get('owner', '')}")
                # マーケットプレイスの成績参考値
                logic_key = selected_logic_saved.get("_logic_key", "")
                listing = marketplace_store.get_listing(logic_key)
                if listing:
                    bt = listing.get("backtest_win" if bet_type_saved == "単勝" else "backtest_place", {})
                    if bt:
                        st.caption(f"参考: 的中率 {bt.get('的中率', '-')}% / 回収率 {bt.get('回収率', '-')}%")

        # フォワード成績への保存
        st.divider()
        if st.button("この予想をフォワード成績に保存", key="pred_save_forward"):
            _save_to_forward(selected_logic_saved, race_info_saved, pick, bet_type_saved)

    # リセット
    if st.button("新しい予想を始める", key="pred_reset"):
        for key in list(st.session_state.keys()):
            if key.startswith("pred_") or key.startswith("_pred_"):
                del st.session_state[key]
        st.rerun()


def _show_logic_detail(rec: dict):
    """自分のロジック詳細表示"""
    OP_MAP = {"eq": "=", "le": "<=", "ge": ">=", "lt": "<", "gt": ">", "in": "含む"}

    scope = rec.get("scope", {})
    if scope:
        st.markdown("**Scope**")
        items = []
        d_min = scope.get("distance_min")
        d_max = scope.get("distance_max")
        if d_min is not None and d_max is not None:
            items.append(f"距離: {d_min}m〜{d_max}m")
        for label, key in [("競馬場", "venues"), ("芝/ダート", "surface"),
                           ("クラス", "race_class"), ("年齢条件", "age_condition")]:
            vals = scope.get(key, [])
            if vals:
                items.append(f"{label}: {', '.join(vals)}")
        st.write(" | ".join(items))

    must = rec.get("must")
    if must and must.get("blocks"):
        st.markdown("**Must（除外条件）**")
        for bi, block in enumerate(must["blocks"]):
            conds = block.get("conditions", [])
            if conds:
                parts = []
                for c in conds:
                    op = OP_MAP.get(c.get("operator", ""), c.get("operator", ""))
                    parts.append(f"{c.get('category', '')} {op} {c.get('value', '')}")
                st.write(f"グループ{bi + 1} (OR): {' / '.join(parts)}")

    pa = rec.get("prefer_avoid")
    if pa:
        prefer = pa.get("prefer", [])
        avoid = pa.get("avoid", [])
        if prefer:
            st.markdown("**Prefer（優先）**")
            for p in sorted(prefer, key=lambda x: x.get("order", 999)):
                cr = p.get("criteria", {})
                op = OP_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
                st.write(f"{p.get('order', '?')}. {p.get('name', '')} — {cr.get('category', '')} {op} {cr.get('value', '')}")
        if avoid:
            st.markdown("**Avoid（回避）**")
            for a in avoid:
                cr = a.get("criteria", {})
                op = OP_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
                st.write(f"- {a.get('name', '')} — {cr.get('category', '')} {op} {cr.get('value', '')}")


def _save_to_forward(logic_rec: dict, race_info: dict, pick, bet_type: str):
    """予想結果をフォワード成績に保存"""
    from datetime import date
    from logic_store import save_forward_result
    from models.forward_record import ForwardResult

    logic_name = logic_rec.get("name", "")
    owner = logic_rec.get("owner", "")

    result = ForwardResult(
        race_id=f"pred_{date.today().isoformat()}",
        race_date=date.today().isoformat(),
        race_name=f"{race_info.get('venue', '')} {race_info.get('distance', '')}m {race_info.get('surface', '')}",
        bet_type=bet_type,
        horse_name=pick.horse_name,
        horse_number=pick.horse_number,
        bet_amount=100,
        is_hit=False,  # 結果は後で更新
        payout=0,
    )
    save_forward_result(logic_name, result, owner=owner)
    st.success(f"フォワード成績に保存しました（結果は後で「コミュニティ」ページから更新できます）。")
