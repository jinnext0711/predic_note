"""
Turf Intelligence Office - 競馬予想プロセス記録 × シミュレーション基盤
Streamlit UI エントリポイント（マルチページ構成）
"""
import sys
from pathlib import Path

# プロジェクトルートで streamlit run したときに src 内のモジュールを読むため
_src = Path(__file__).resolve().parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import streamlit as st

st.set_page_config(
    page_title="Turf Intelligence Office",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# カスタムCSSは各ページのinject_custom_css()で注入される

# ── 認証フロー ──
from auth_store import register_user, authenticate_user

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if st.session_state.auth_user is None:
    from pages.styles import inject_custom_css
    inject_custom_css()

    # ヒーローヘッダー
    st.markdown(
        '<div class="login-hero">'
        '<div class="brand-name">TURF INTELLIGENCE<br>OFFICE</div>'
        '<div class="brand-sub">DATA-DRIVEN HORSE RACING INTELLIGENCE</div>'
        '<div class="tagline">競馬の知性を、あなたの武器に。</div>'
        '<div class="tagline-sub">Record ・ Verify ・ Predict</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 中央寄せのログインフォーム
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        auth_tab = st.radio("アカウント", ["ログイン", "新規登録"], horizontal=True, key="auth_tab", label_visibility="collapsed")

        if auth_tab == "ログイン":
            st.subheader("ログイン")
            login_user = st.text_input("ユーザー名", key="login_username")
            login_pass = st.text_input("パスワード", type="password", key="login_password")
            if st.button("ログイン", type="primary", use_container_width=True, key="login_btn"):
                ok, msg = authenticate_user(login_user, login_pass)
                if ok:
                    st.session_state.auth_user = login_user.strip()
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.subheader("新規登録")
            st.caption("アカウントを作成して、ロジックの記録・検証を始めましょう。")
            reg_user = st.text_input("ユーザー名（3文字以上）", key="reg_username")
            reg_pass = st.text_input("パスワード（6文字以上）", type="password", key="reg_password")
            reg_pass2 = st.text_input("パスワード（確認）", type="password", key="reg_password2")
            if st.button("登録", type="primary", use_container_width=True, key="reg_btn"):
                if reg_pass != reg_pass2:
                    st.error("パスワードが一致しません。")
                else:
                    ok, msg = register_user(reg_user, reg_pass)
                    if ok:
                        st.success(msg + " ログインしてください。")
                    else:
                        st.error(msg)

    st.stop()

# ── ログイン済み ──

# サイドバー: ユーザー情報
from auth_store import is_paid_user as _check_paid, get_backtest_count as _get_bt_count, FREE_BACKTEST_LIMIT
from point_store import get_points as _get_points

_current_user = st.session_state.auth_user
_user_is_paid = _check_paid(_current_user)
_plan_label = "有料プラン" if _user_is_paid else "無料プラン"
_plan_cls = "plan-paid" if _user_is_paid else "plan-free"
_user_points = _get_points(_current_user)

# サイドバーブランドヘッダー
st.sidebar.markdown(
    '<div class="sidebar-brand">'
    '<div class="brand-main">TURF</div>'
    '<div class="brand-sub">Intelligence Office</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.sidebar.divider()

# ユーザー情報カード
st.sidebar.markdown(
    f'<div class="sidebar-user-card">'
    f'<div class="user-name">{_current_user}</div>'
    f'<span class="plan-badge {_plan_cls}">{_plan_label}</span>'
    f'<div class="user-points">💰 {_user_points:,} pt</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.sidebar.divider()

# サイドバー: ナビゲーション（8項目）
_pages = ["ホーム", "ロジック作成", "マイロジック", "バックテスト",
          "予想", "マーケットプレイス", "コミュニティ", "仕様書"]
if "nav_page" in st.session_state and st.session_state.nav_page in _pages:
    st.session_state["nav_radio"] = st.session_state.pop("nav_page")

nav = st.sidebar.radio(
    "メニュー",
    _pages,
    key="nav_radio",
    label_visibility="collapsed",
    captions=[
        "使い方・概要",
        "新しいロジックを作る",
        "保存済みロジックの管理",
        "過去データで検証",
        "ロジックで予想を実行",
        "アルゴリズム売買",
        "公開ロジック・成績記録",
        "MVP仕様",
    ],
)

st.sidebar.divider()

# BT残回数（無料ユーザーのみ）
if not _user_is_paid:
    _bt_used = _get_bt_count(_current_user)
    _bt_remaining = max(0, FREE_BACKTEST_LIMIT - _bt_used)
    st.sidebar.caption(f"BT残回数: {_bt_remaining}/{FREE_BACKTEST_LIMIT}")

# ログアウト
if st.sidebar.button("ログアウト", key="logout_btn", use_container_width=True):
    # ユーザー固有のセッション状態をすべてクリア
    keys_to_clear = [k for k in list(st.session_state.keys())
                     if k.startswith(("wiz_", "bt_", "cv_", "mylogic_", "fw_", "pub_", "nav_", "pred_", "mp_"))]
    for k in keys_to_clear:
        del st.session_state[k]
    st.session_state.auth_user = None
    st.rerun()

# ページルーティング
if nav == "ホーム":
    from pages.home import render
    render()
elif nav == "ロジック作成":
    from pages.create_logic import render
    render()
elif nav == "マイロジック":
    from pages.my_logics import render
    render()
elif nav == "バックテスト":
    from pages.backtest import render
    render()
elif nav == "予想":
    from pages.prediction import render
    render()
elif nav == "マーケットプレイス":
    from pages.marketplace import render
    render()
elif nav == "コミュニティ":
    from pages.community import render
    render()
elif nav == "仕様書":
    from pages.spec import render
    render()
