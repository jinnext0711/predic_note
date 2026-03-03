"""
コミュニティ画面 - 公開ロジック閲覧・フォワード成績。
"""
import streamlit as st
from pages.styles import inject_custom_css, show_help

OP_DISPLAY_MAP = {"eq": "=", "le": "<=", "ge": ">=", "lt": "<", "gt": ">", "in": "含む"}


def render():
    inject_custom_css()

    st.header("コミュニティ")

    tab_public, tab_forward = st.tabs(["公開ロジック", "フォワード成績"])

    with tab_public:
        _render_public_logics()

    with tab_forward:
        _render_forward_records()


def _render_public_logics():
    """公開ロジック一覧"""
    show_help("他のユーザーが公開しているロジックを閲覧・バックテストできます。")

    try:
        from logic_store import list_public_logics
        from simulation import check_simulatable
        public_logics = list_public_logics()
        current_user = st.session_state.get("auth_user", "")
        other_logics = [r for r in public_logics if r.get("owner", "") != current_user]

        if not other_logics:
            if not public_logics:
                st.info("現在公開されているロジックはありません。")
            else:
                st.info("他のユーザーの公開ロジックはまだありません。")
            return

        pub_names = [r.get("name", "") for r in other_logics]
        pub_owners = {r.get("name", ""): r.get("owner", "（不明）") for r in other_logics}
        selected = st.selectbox("公開ロジックを選択", pub_names, key="pub_select")
        pub_rec = next((r for r in other_logics if r.get("name") == selected), None)

        if pub_rec:
            owner_name = pub_owners.get(selected, '（不明）')
            created = pub_rec.get("created_at", "")
            meta_parts = [f"作成者: {owner_name}"]
            if created:
                meta_parts.append(f"作成日: {created[:10]}")
            st.caption(" | ".join(meta_parts))
            desc = pub_rec.get("description", "")
            if desc:
                st.markdown(f"> {desc}")

            can_sim, reason = check_simulatable(pub_rec)
            if can_sim:
                st.success("バックテスト可能")
            else:
                st.warning(f"バックテスト不可（{reason}）")

            # バックテスト実行
            if can_sim:
                st.divider()
                from models.simulation_spec import BetType
                from simulation import run_backtest
                from auth_store import can_run_backtest, increment_backtest_count, is_paid_user

                bet_label = st.radio("券種", ["単勝", "複勝"], horizontal=True, key="pub_bet")
                bet_type = BetType.WIN if bet_label == "単勝" else BetType.PLACE

                if st.button("バックテストを実行", key="pub_bt_run"):
                    can_run, msg = can_run_backtest(current_user, is_own_logic=False)
                    if not can_run:
                        st.warning(msg)
                    else:
                        if msg:
                            st.info(msg)
                        try:
                            with st.spinner("バックテスト実行中..."):
                                result = run_backtest(pub_rec, bet_type)
                        except ValueError as ve:
                            st.error(f"エラー: {ve}")
                            return
                        if not is_paid_user(current_user):
                            increment_backtest_count(current_user)

                        # 結果表示（backtest.pyの共通関数を使用）
                        from pages.backtest import render_result
                        render_result(result, selected, bet_label)

            # Scope 詳細
            st.divider()
            _render_logic_detail(pub_rec)

    except Exception as e:
        st.error("予期しないエラーが発生しました。ページを再読み込みしてください。")
        import logging
        logging.getLogger(__name__).exception("public logics error")


def _render_forward_records():
    """フォワード成績"""
    show_help(
        "実際の予想結果（的中/不的中・払戻金額）を記録できます。<br>"
        "バックテスト不可のロジックでも、フォワード成績は記録できます。"
    )

    try:
        from logic_store import list_names, load_forward_record, save_forward_result, delete_forward_result
        from models.forward_record import ForwardResult

        _fw_owner = st.session_state.get("auth_user", "")
        names = list_names(owner=_fw_owner)
        if not names:
            st.warning("先にロジックを作成してください。")
            return

        selected = st.selectbox("対象ロジック", names, key="fw_logic")

        # 成績サマリ
        record = load_forward_record(selected, owner=_fw_owner)
        if record and record.results:
            st.subheader("成績サマリ")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("試行回数", f"{record.total_trials()} 回")
            with c2:
                st.metric("的中率", f"{record.hit_rate():.1f}%")
            with c3:
                st.metric("回収率", f"{record.recovery_rate():.1f}%")
            with c4:
                st.metric("総損益", f"{record.total_profit():+,.0f} 円")

            # 成績一覧
            st.subheader("成績一覧")
            for i, r in enumerate(reversed(record.results)):
                idx = len(record.results) - 1 - i
                hit_mark = "○" if r.is_hit else "×"
                profit = r.profit()
                profit_str = f"{profit:+,.0f}円"
                with st.expander(
                    f"{r.race_date} {r.race_name or ''} | {r.bet_type} {r.horse_name} | {hit_mark} {profit_str}",
                    expanded=False,
                ):
                    st.write(f"レースID: {r.race_id}")
                    st.write(f"馬番: {r.horse_number or '―'}")
                    st.write(f"賭け金: {r.bet_amount:,}円 | 払戻: {r.payout:,.0f}円")
                    if st.button("この記録を削除", key=f"fw_del_{idx}"):
                        delete_forward_result(selected, idx, owner=_fw_owner)
                        st.rerun()
        else:
            st.info("まだ成績が記録されていません。下のフォームから記録を追加してください。")

        # 新規記録フォーム
        st.divider()
        st.subheader("成績を記録")
        with st.form("fw_add_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                race_id = st.text_input(
                    "レースID",
                    placeholder="例: 202501010101",
                    help="netkeibaのレースURL末尾の12桁の数字（年4桁+開催コード8桁）",
                )
                race_date = st.date_input("レース日")
                race_name = st.text_input("レース名", placeholder="例: 東京5R")
                bet_type = st.selectbox(
                    "券種", ["単勝", "複勝"],
                    help="単勝: 1着を当てる / 複勝: 3着以内を当てる",
                )
            with fc2:
                horse_name = st.text_input("予想馬名", placeholder="例: サンプルホース")
                horse_number = st.number_input("馬番", min_value=1, max_value=18, value=1)
                bet_amount = st.number_input("賭け金（円）", min_value=100, value=100, step=100)
                is_hit = st.checkbox(
                    "的中した",
                    help="単勝: 1着なら的中 / 複勝: 3着以内なら的中",
                )
                payout = st.number_input(
                    "払戻金額（円）", min_value=0, value=0, step=10,
                    help="実際に受け取った払戻金額を入力（不的中なら0）",
                )

            submitted = st.form_submit_button("記録を保存")
            if submitted:
                if not race_id.strip():
                    st.warning("レースIDを入力してください。")
                elif not horse_name.strip():
                    st.warning("予想馬名を入力してください。")
                else:
                    result = ForwardResult(
                        race_id=race_id.strip(),
                        race_date=race_date.isoformat(),
                        race_name=race_name.strip() if race_name else None,
                        bet_type=bet_type,
                        horse_name=horse_name.strip(),
                        horse_number=int(horse_number),
                        bet_amount=int(bet_amount),
                        is_hit=bool(is_hit),
                        payout=float(payout),
                    )
                    save_forward_result(selected, result, owner=_fw_owner)
                    st.success("成績を記録しました。")
                    st.rerun()
    except Exception as e:
        st.error("予期しないエラーが発生しました。ページを再読み込みしてください。")
        import logging
        logging.getLogger(__name__).exception("forward records error")


def _render_logic_detail(rec: dict):
    """ロジック詳細の読み取り専用表示"""
    with st.expander("ロジック詳細を見る", expanded=False):
        # Scope
        st.markdown("**レース条件**")
        scope = rec.get("scope")
        if scope:
            cols = st.columns(5)
            with cols[0]:
                st.markdown("**距離**")
                d_min = scope.get("distance_min")
                d_max = scope.get("distance_max")
                if d_min is not None and d_max is not None:
                    st.write(f"{d_min}m 〜 {d_max}m")
                else:
                    st.write("（未設定）")
            for col, (label, key) in zip(cols[1:], [
                ("競馬場", "venues"), ("芝/ダート", "surface"),
                ("クラス", "race_class"), ("年齢条件", "age_condition"),
            ]):
                with col:
                    vals = scope.get(key, [])
                    st.markdown(f"**{label}**")
                    st.write(", ".join(vals) if vals else "（未設定）")

        # Must
        st.markdown("**除外条件**")
        must = rec.get("must")
        if must and must.get("blocks"):
            for bi, block in enumerate(must["blocks"]):
                conds = block.get("conditions", [])
                if conds:
                    cond_strs = []
                    for c in conds:
                        op_label = OP_DISPLAY_MAP.get(c.get("operator", ""), c.get("operator", ""))
                        cond_strs.append(f"{c.get('category', '')} {op_label} {c.get('value', '')}")
                    st.markdown(f"グループ {bi + 1} (OR): " + " / ".join(cond_strs))
        else:
            st.caption("（未設定）")

        # Prefer/Avoid
        st.markdown("**優先/回避**")
        pa = rec.get("prefer_avoid")
        if pa:
            for p in sorted(pa.get("prefer", []), key=lambda x: x.get("order", 999)):
                cr = p.get("criteria", {})
                op_label = OP_DISPLAY_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
                st.write(f"Prefer {p.get('order', '?')}: {p.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
            for a in pa.get("avoid", []):
                cr = a.get("criteria", {})
                op_label = OP_DISPLAY_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
                st.write(f"Avoid: {a.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
        else:
            st.caption("（未設定）")
