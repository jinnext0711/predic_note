"""
マーケットプレイス画面 - アルゴリズムの売買。
"""
import streamlit as st
from pages.styles import inject_custom_css, show_help


def render():
    inject_custom_css()

    username = st.session_state.get("auth_user", "")
    st.header("マーケットプレイス")

    from point_store import get_points
    current_points = get_points(username)
    st.markdown(f"**ポイント残高: {current_points:,} pt**")

    tab_browse, tab_purchased, tab_manage = st.tabs(
        ["アルゴリズムを探す", "購入済み", "出品管理"]
    )

    with tab_browse:
        _render_browse(username)
    with tab_purchased:
        _render_purchased(username)
    with tab_manage:
        _render_manage(username)


def _get_scope_summary(logic_key: str) -> str:
    """ロジックキーからScope情報のサマリ文字列を生成する。"""
    import logic_store
    owner = logic_key.split("::", 1)[0] if "::" in logic_key else ""
    name = logic_key.split("::", 1)[1] if "::" in logic_key else logic_key
    rec = logic_store.get_logic(name, owner=owner)
    if not rec:
        return ""
    scope = rec.get("scope", {})
    if not scope:
        return ""
    parts = []
    venues = scope.get("venues", [])
    if venues:
        parts.append("場: " + "・".join(venues))
    surface = scope.get("surface", [])
    if surface:
        parts.append("/".join(surface))
    d_min = scope.get("distance_min")
    d_max = scope.get("distance_max")
    if d_min is not None and d_max is not None:
        parts.append(f"{d_min}-{d_max}m")
    race_class = scope.get("race_class", [])
    if race_class:
        parts.append("・".join(race_class))
    age = scope.get("age_condition", [])
    if age:
        parts.append("・".join(age))
    return " | ".join(parts)


def _render_browse(username: str):
    """アルゴリズム一覧・購入"""
    import marketplace_store
    from auth_store import get_purchased_logics

    listings = marketplace_store.load_listings()
    if not listings:
        st.info("現在出品されているアルゴリズムはありません。")
        return

    # ソート
    sort_option = st.selectbox(
        "並び替え",
        ["回収率（単勝）順", "的中率（単勝）順", "価格が安い順", "購入者数順"],
        key="mp_sort",
    )

    listing_items = list(listings.items())
    if sort_option == "回収率（単勝）順":
        listing_items.sort(key=lambda x: x[1].get("backtest_win", {}).get("回収率", 0), reverse=True)
    elif sort_option == "的中率（単勝）順":
        listing_items.sort(key=lambda x: x[1].get("backtest_win", {}).get("的中率", 0), reverse=True)
    elif sort_option == "価格が安い順":
        listing_items.sort(key=lambda x: x[1].get("price", 0))
    elif sort_option == "購入者数順":
        listing_items.sort(key=lambda x: x[1].get("purchase_count", 0), reverse=True)

    purchased_keys = get_purchased_logics(username)

    for logic_key, listing in listing_items:
        seller = listing.get("seller", "")
        # 自分の出品はスキップ（出品管理タブで見る）
        if seller == username:
            continue

        price = listing.get("price", 0)
        desc = listing.get("description_short", "")
        bt_win = listing.get("backtest_win", {})
        bt_place = listing.get("backtest_place", {})
        purchase_count = listing.get("purchase_count", 0)

        # ロジック名はキーから取得
        logic_name = logic_key.split("::", 1)[1] if "::" in logic_key else logic_key

        with st.container(border=True):
            col_info, col_stats, col_action = st.columns([2, 2, 1])

            with col_info:
                st.markdown(f"### {logic_name}")
                st.caption(f"作者: {seller}")
                if desc:
                    st.write(desc)
                # 対象レース条件を表示
                scope_summary = _get_scope_summary(logic_key)
                if scope_summary:
                    st.caption(f"対象: {scope_summary}")
                st.caption(f"購入者: {purchase_count}人")

            with col_stats:
                st.markdown("**バックテスト成績**")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("単勝")
                    if bt_win:
                        st.write(f"的中率: {bt_win.get('的中率', '-')}%")
                        st.write(f"回収率: {bt_win.get('回収率', '-')}%")
                        st.write(f"試行: {bt_win.get('試行回数', '-')}回")
                    else:
                        st.write("データなし")
                with c2:
                    st.markdown("複勝")
                    if bt_place:
                        st.write(f"的中率: {bt_place.get('的中率', '-')}%")
                        st.write(f"回収率: {bt_place.get('回収率', '-')}%")
                        st.write(f"試行: {bt_place.get('試行回数', '-')}回")
                    else:
                        st.write("データなし")

            with col_action:
                st.markdown(f"**{price:,} pt**")
                already_purchased = logic_key in purchased_keys
                if already_purchased:
                    st.success("購入済み")
                else:
                    buy_key = f"mp_buy_{logic_key}"
                    confirm_key = f"mp_confirm_{logic_key}"

                    if st.session_state.get(confirm_key):
                        st.warning(f"{price:,}pt 消費します。よろしいですか？")
                        c_yes, c_no = st.columns(2)
                        with c_yes:
                            if st.button("購入する", key=f"{buy_key}_yes", type="primary"):
                                ok, msg = marketplace_store.purchase_logic(username, logic_key)
                                if ok:
                                    st.success(msg)
                                    st.session_state.pop(confirm_key, None)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with c_no:
                            if st.button("キャンセル", key=f"{buy_key}_no"):
                                st.session_state.pop(confirm_key, None)
                                st.rerun()
                    else:
                        if st.button("購入する", key=buy_key):
                            st.session_state[confirm_key] = True
                            st.rerun()


def _render_purchased(username: str):
    """購入済みアルゴリズム一覧"""
    from auth_store import get_purchased_logics
    import marketplace_store

    purchased_keys = get_purchased_logics(username)
    if not purchased_keys:
        st.info("まだ購入したアルゴリズムはありません。")
        show_help("「アルゴリズムを探す」タブで他のユーザーのアルゴリズムを購入できます。")
        return

    listings = marketplace_store.load_listings()

    for logic_key in purchased_keys:
        listing = listings.get(logic_key, {})
        logic_name = logic_key.split("::", 1)[1] if "::" in logic_key else logic_key
        seller = logic_key.split("::", 1)[0] if "::" in logic_key else ""

        with st.container(border=True):
            col_info, col_stats, col_link = st.columns([2, 2, 1])

            with col_info:
                st.markdown(f"### {logic_name}")
                st.caption(f"作者: {seller}")
                # 対象レース条件を表示
                scope_summary = _get_scope_summary(logic_key)
                if scope_summary:
                    st.caption(f"対象: {scope_summary}")

            with col_stats:
                bt_win = listing.get("backtest_win", {})
                bt_place = listing.get("backtest_place", {})
                if bt_win or bt_place:
                    c1, c2 = st.columns(2)
                    with c1:
                        if bt_win:
                            st.write(f"単勝 的中率: {bt_win.get('的中率', '-')}%  回収率: {bt_win.get('回収率', '-')}%")
                    with c2:
                        if bt_place:
                            st.write(f"複勝 的中率: {bt_place.get('的中率', '-')}%  回収率: {bt_place.get('回収率', '-')}%")

            with col_link:
                if st.button("予想で使う", key=f"mp_use_{logic_key}"):
                    st.session_state.nav_page = "予想"
                    st.rerun()


def _render_manage(username: str):
    """出品管理（自分のロジック）"""
    import marketplace_store
    import logic_store
    from simulation import check_simulatable

    listings = marketplace_store.load_listings()

    # 自分の出品中一覧
    my_listings = {k: v for k, v in listings.items() if v.get("seller") == username}

    st.subheader("出品中")
    if my_listings:
        for logic_key, listing in my_listings.items():
            logic_name = logic_key.split("::", 1)[1] if "::" in logic_key else logic_key
            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**{logic_name}**")
                    st.write(f"価格: {listing.get('price', 0):,} pt | 購入者: {listing.get('purchase_count', 0)}人")
                    st.caption(listing.get("description_short", ""))

                with col_action:
                    # 価格変更
                    new_price = st.number_input(
                        "新価格", min_value=1, value=listing.get("price", 100),
                        key=f"mp_price_{logic_key}",
                    )
                    if st.button("価格変更", key=f"mp_chprice_{logic_key}"):
                        marketplace_store.update_listing_price(logic_key, new_price)
                        st.success("価格を変更しました。")
                        st.rerun()

                    if st.button("出品取り下げ", key=f"mp_delist_{logic_key}"):
                        marketplace_store.delist_marketplace(logic_key)
                        st.success("出品を取り下げました。")
                        st.rerun()
    else:
        st.info("出品中のアルゴリズムはありません。")

    st.divider()

    # 新規出品
    st.subheader("新規出品")
    all_logics = logic_store.load_all()
    my_logics = [r for r in all_logics if r.get("owner") == username]
    # バックテスト可能 + 未出品のもの
    listable = []
    for rec in my_logics:
        can_sim, _ = check_simulatable(rec)
        if not can_sim:
            continue
        key = f"{rec.get('owner', '')}::{rec.get('name', '')}"
        if key in listings:
            continue
        listable.append(rec)

    if not listable:
        st.info("出品可能なロジックがありません。バックテスト可能で未出品のロジックが対象です。")
        return

    listable_names = [r.get("name", "") for r in listable]
    selected_name = st.selectbox("出品するロジック", listable_names, key="mp_list_select")
    selected_rec = next((r for r in listable if r.get("name") == selected_name), None)

    if selected_rec:
        desc_short = st.text_area(
            "説明文（ロジック詳細は非公開です）",
            max_chars=200,
            key="mp_list_desc",
        )
        price = st.number_input("価格（ポイント）", min_value=1, value=100, key="mp_list_price")

        # バックテスト成績の取得
        from simulation import run_backtest
        from models.simulation_spec import BetType

        st.caption("出品前にバックテスト成績を自動計算します。")

        if st.button("出品する", type="primary", key="mp_list_submit"):
            if not desc_short.strip():
                st.error("説明文を入力してください。")
            else:
                with st.spinner("バックテスト実行中..."):
                    try:
                        bt_win = run_backtest(selected_rec, BetType.WIN)
                        bt_place = run_backtest(selected_rec, BetType.PLACE)
                        bt_win_summary = {
                            "試行回数": bt_win["試行回数"],
                            "的中率": bt_win["的中率"],
                            "回収率": bt_win["回収率"],
                        }
                        bt_place_summary = {
                            "試行回数": bt_place["試行回数"],
                            "的中率": bt_place["的中率"],
                            "回収率": bt_place["回収率"],
                        }
                    except Exception as e:
                        st.error(f"バックテスト実行エラー: {e}")
                        return

                logic_key = f"{username}::{selected_name}"
                ok = marketplace_store.list_marketplace(
                    logic_key=logic_key,
                    seller=username,
                    price=price,
                    description_short=desc_short.strip(),
                    backtest_win=bt_win_summary,
                    backtest_place=bt_place_summary,
                )
                if ok:
                    st.success(f"「{selected_name}」を{price:,}ptで出品しました。")
                    st.rerun()
                else:
                    st.error("出品に失敗しました（既に出品済みの可能性があります）。")

    # 売上履歴
    st.divider()
    st.subheader("売上履歴")
    sales = marketplace_store.get_seller_sales(username)
    if sales:
        import pandas as pd
        df = pd.DataFrame(sales)
        df = df.rename(columns={
            "logic_key": "ロジック", "buyer": "購入者",
            "price": "金額(pt)", "at": "日時",
        })
        df = df.drop(columns=["seller"], errors="ignore")
        st.dataframe(df, use_container_width=True, hide_index=True)
        total_sales = sum(s.get("price", 0) for s in sales)
        st.metric("売上合計", f"{total_sales:,} pt")
    else:
        st.info("まだ売上はありません。")
