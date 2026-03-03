"""
バックテスト画面 - シミュレーション実行と結果表示（グラフ付き）。
"""
import streamlit as st
import pandas as pd
from pages.styles import inject_custom_css, show_help


def render():
    inject_custom_css()

    st.header("バックテスト")

    show_help(
        "ロジックの成績を過去のレースデータで検証します。<br>"
        "ロジック作成後、ここでバックテストを実行すると、"
        "的中率・回収率がわかります。"
    )

    try:
        from logic_store import load_all
        from simulation import check_simulatable, run_backtest, get_logic_type_info
        from models.simulation_spec import BetType

        _all_logics = load_all()
        _sim_user = st.session_state.get("auth_user", "")
        logics = [r for r in _all_logics if r.get("owner", "") == _sim_user]

        if not logics:
            st.info("まだロジックがありません。「ロジック作成」ページからロジックを作成してください。")
            return

        # シミュレーション可能なロジックのみフィルタ
        simulatable = []
        non_simulatable = []
        for rec in logics:
            info = get_logic_type_info(rec)
            if info["can_simulate"]:
                simulatable.append(rec)
            else:
                non_simulatable.append(rec)

        if not simulatable:
            st.warning("バックテスト可能なロジックがありません。")
            if non_simulatable:
                st.caption("以下のロジックはバックテスト不可です:")
                for rec in non_simulatable:
                    _, reason = check_simulatable(rec)
                    st.markdown(f"- **{rec.get('name', '')}**: {reason}")
            return

        # ロジック選択（他ページからの遷移で無効な値が入っていたらクリア）
        sim_names = [r.get("name", "") for r in simulatable]
        if "bt_logic" in st.session_state and st.session_state.bt_logic not in sim_names:
            del st.session_state["bt_logic"]
        selected_logic = st.selectbox("対象ロジック", sim_names, key="bt_logic")

        # ロジック変更時に古い結果をクリア
        if st.session_state.get("bt_result_name") and st.session_state.bt_result_name != selected_logic:
            st.session_state.pop("bt_result", None)
            st.session_state.pop("bt_result_name", None)
            st.session_state.pop("bt_result_bet", None)

        # 券種選択
        bet_label = st.radio("券種", ["単勝", "複勝"], horizontal=True, key="bt_bet_type")
        bet_type = BetType.WIN if bet_label == "単勝" else BetType.PLACE

        st.caption("単勝: 1着を当てる / 複勝: 3着以内を当てる")

        # 実行ボタン（連打防止）
        _bt_running = st.session_state.get("bt_running", False)
        if st.button("バックテストを実行", type="primary", key="bt_run", disabled=_bt_running):
            from auth_store import can_run_backtest, increment_backtest_count
            current_user = st.session_state.get("auth_user", "")
            target_rec = next((r for r in simulatable if r.get("name") == selected_logic), None)

            if target_rec is None:
                st.error("ロジックが見つかりません。")
                return

            is_own = target_rec.get("owner", "") == current_user
            can_run, plan_msg = can_run_backtest(current_user, is_own)

            if not can_run:
                st.warning(plan_msg)
                return

            if plan_msg:
                st.info(plan_msg)

            try:
                st.session_state.bt_running = True
                with st.spinner("バックテスト実行中...（レースデータを検証しています）"):
                    result = run_backtest(target_rec, bet_type)
            except ValueError as ve:
                st.error(f"エラー: {ve}")
                return
            finally:
                st.session_state.bt_running = False

            if not is_own:
                increment_backtest_count(current_user)

            # 結果をセッションに保存
            st.session_state.bt_result = result
            st.session_state.bt_result_name = selected_logic
            st.session_state.bt_result_bet = bet_label

        # 結果表示
        if "bt_result" in st.session_state and st.session_state.get("bt_result_name") == selected_logic:
            render_result(
                st.session_state.bt_result,
                st.session_state.bt_result_name,
                st.session_state.bt_result_bet,
            )

        # バックテスト不可ロジック
        if non_simulatable:
            st.divider()
            with st.expander("バックテスト不可のロジック"):
                for rec in non_simulatable:
                    _, reason = check_simulatable(rec)
                    st.markdown(f"- **{rec.get('name', '')}**: {reason}")
                st.caption("カスタム変数を含むロジックはバックテストできません。フォワード成績で記録してください。")

    except Exception as e:
        st.error("予期しないエラーが発生しました。ページを再読み込みしてください。")
        import logging
        logging.getLogger(__name__).exception("backtest page error")


def diagnose(result: dict, bet_label: str) -> str:
    """回収率×的中率から具体的な改善アドバイスを生成"""
    recovery = result.get("回収率", 0)
    hit_rate = result.get("的中率", 0)
    trials = result.get("試行回数", 0)

    advices = []

    # サンプルサイズ警告
    confidence = result.get("信頼度", "")
    if confidence == "low":
        advices.append(
            "**サンプル数が少ない**（{0}回）ため、結果の信頼度が低めです。"
            "対象レース条件を広げるか、データ期間を増やすと精度が上がります。".format(trials)
        )

    # 回収率×的中率の診断
    if recovery >= 110:
        advices.append(
            "好成績です。「コミュニティ」ページのフォワード成績で"
            "実際のレースでも検証してみましょう。"
        )
    elif recovery >= 100:
        advices.append(
            "プラス収支ですが、微差です。必須条件や優先条件を"
            "微調整して安定性を高めてみましょう。"
        )
    elif hit_rate < 15:
        advices.append(
            "的中率が低めです。必須条件が厳しすぎる可能性があります。"
            "条件を少し緩めるか、対象レースを増やしてみましょう。"
        )
    elif hit_rate >= 30 and recovery < 80:
        advices.append(
            "的中はしているが回収率が低いです。"
            "オッズ帯の条件を追加して、低配当の馬を避けると改善する可能性があります。"
        )
        if bet_label == "複勝":
            advices.append(
                "単勝に切り替えると、的中時の配当が上がり回収率が改善する場合があります。"
            )
    else:
        advices.append(
            "必須条件の見直しや、優先条件の追加・順序変更で改善できる可能性があります。"
        )

    # 複勝の注意
    if bet_label == "複勝":
        advices.append(
            "※ 複勝オッズは単勝オッズからの推定値です。実際のオッズとは異なる場合があります。"
        )

    return "\n\n".join(advices)


def render_result(result: dict, logic_name: str, bet_label: str):
    """バックテスト結果の表示（メトリクス + 診断 + グラフ）"""

    st.divider()
    st.subheader(f"バックテスト結果: {logic_name}（{bet_label}）")

    trials = result.get("試行回数", 0)
    if trials == 0:
        st.warning("対象レースが0件でした。対象レース条件を広げてみてください。")
        return

    # サンプル信頼度バナー
    confidence = result.get("信頼度", "")
    if confidence == "low":
        st.warning(f"サンプル数: {trials}回（信頼度: 低） - 結果は参考値としてご覧ください")
    elif confidence == "medium":
        st.info(f"サンプル数: {trials}回（信頼度: 中）")

    # メインメトリクス
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("試行回数", f"{trials} 回")
    with col2:
        recovery = result.get("回収率", 0)
        st.metric("回収率", f"{recovery}%", delta=f"{recovery-100:+.1f}%")
    with col3:
        st.metric("的中率", f"{result.get('的中率', 0)}%")

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("最大ドローダウン", f"{result.get('最大ドローダウン', 0):,.0f} 円")
    with col5:
        st.metric("最大連敗数", f"{result.get('最大連敗数', 0)} 連敗")
    with col6:
        st.metric("最大連勝数", f"{result.get('最大連勝数', 0)} 連勝")

    # 追加指標
    col7, col8 = st.columns(2)
    with col7:
        avg_profit = result.get("平均利益", 0)
        st.metric("1試行あたり平均利益", f"{avg_profit:+,.1f} 円")
    with col8:
        pf = result.get("Profit Factor", 0)
        import math
        pf_str = "∞（全勝）" if math.isinf(pf) else f"{pf:.2f}"
        st.metric("Profit Factor", pf_str, help="総利益÷総損失。1.0以上でプラス収支")

    # 診断アドバイス
    st.divider()
    st.subheader("診断・アドバイス")
    advice = diagnose(result, bet_label)
    st.markdown(advice)

    # 年別推移
    yearly = result.get("年別推移", [])
    if yearly:
        st.divider()
        st.subheader("年別推移")

        df = pd.DataFrame(yearly)

        # テーブル表示
        df_display = df.rename(columns={
            "年": "年度",
            "試行回数": "試行数",
            "的中率": "的中率(%)",
            "回収率": "回収率(%)",
        })
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # グラフ表示
        if len(yearly) >= 2:
            st.subheader("推移グラフ")

            tab_recovery, tab_hit = st.tabs(["回収率", "的中率"])

            with tab_recovery:
                chart_data = pd.DataFrame({
                    "年度": [str(y["年"]) for y in yearly],
                    "回収率(%)": [y["回収率"] for y in yearly],
                })
                st.bar_chart(chart_data, x="年度", y="回収率(%)", color="#1a73e8")
                st.caption("100%を超えていればプラス収支")

            with tab_hit:
                chart_data2 = pd.DataFrame({
                    "年度": [str(y["年"]) for y in yearly],
                    "的中率(%)": [y["的中率"] for y in yearly],
                })
                st.bar_chart(chart_data2, x="年度", y="的中率(%)", color="#2e7d32")
