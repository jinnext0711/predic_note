"""
predic_keiba - 競馬予想プロセス記録 × シミュレーション基盤
Streamlit UI: ロジック記録・Scope / Must / Prefer-Avoid 設定・シミュレーション可否表示
"""
import sys
from pathlib import Path
# プロジェクトルートで streamlit run したときに src 内のモジュールを読むため
_src = Path(__file__).resolve().parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import streamlit as st
from constants.scope_options import (
    VENUES,
    DISTANCE_CATEGORIES,
    SURFACE_TYPES,
    RACE_CLASSES,
    AGE_CONDITIONS,
)
from constants.derived_indicators import DERIVED_INDICATORS, RACE_PACE_CLASSES
from constants.bloodline_options import (
    SIRE_LINE_CATEGORIES,
    DISTANCE_APTITUDE_BLOOD,
    SURFACE_APTITUDE_BLOOD,
)

# 演算子の表示ラベルマッピング（各画面で共通利用）
OP_DISPLAY_MAP = {"eq": "=", "le": "<=", "ge": ">=", "lt": "<", "gt": ">", "in": "含む"}

st.set_page_config(
    page_title="predic_keiba",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏇 predic_keiba")
st.caption("中央競馬に特化した「予想思考の構造化 × 過去検証可能な意思決定基盤」")

# ── 認証フロー ──
from auth_store import register_user, authenticate_user

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if st.session_state.auth_user is None:
    # 未ログイン: 登録・ログイン画面を表示
    auth_tab = st.radio("", ["ログイン", "新規登録"], horizontal=True, key="auth_tab")

    if auth_tab == "ログイン":
        st.subheader("ログイン")
        login_user = st.text_input("ユーザー名", key="login_username")
        login_pass = st.text_input("パスワード", type="password", key="login_password")
        if st.button("ログイン", key="login_btn"):
            ok, msg = authenticate_user(login_user, login_pass)
            if ok:
                st.session_state.auth_user = login_user.strip()
                st.rerun()
            else:
                st.error(msg)
    else:
        st.subheader("新規登録")
        reg_user = st.text_input("ユーザー名（3文字以上）", key="reg_username")
        reg_pass = st.text_input("パスワード（6文字以上）", type="password", key="reg_password")
        reg_pass2 = st.text_input("パスワード（確認）", type="password", key="reg_password2")
        if st.button("登録", key="reg_btn"):
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
# サイドバー: ユーザー情報・ログアウト
from auth_store import is_paid_user as _check_paid, get_backtest_count as _get_bt_count, FREE_BACKTEST_LIMIT
_current_user = st.session_state.auth_user
_user_is_paid = _check_paid(_current_user)
_plan_label = "有料プラン" if _user_is_paid else "無料プラン"
_sidebar_info = f"**ユーザー**: {_current_user}  \n**プラン**: {_plan_label}"
if not _user_is_paid:
    _bt_used = _get_bt_count(_current_user)
    _bt_remaining = max(0, FREE_BACKTEST_LIMIT - _bt_used)
    _sidebar_info += f"  \n**BT残回数**: {_bt_remaining}/{FREE_BACKTEST_LIMIT}"
st.sidebar.markdown(_sidebar_info)
if st.sidebar.button("ログアウト", key="logout_btn"):
    st.session_state.auth_user = None
    st.rerun()

# サイドバー: ナビ
st.sidebar.divider()
nav = st.sidebar.radio(
    "メニュー",
    ["概要", "レース要件（Scope）", "予想ロジック Must", "Prefer / Avoid", "カスタム変数", "ロジック一覧", "公開ロジック", "フォワード成績", "シミュレーション", "仕様書"],
)

if nav == "概要":
    st.header("概要")
    st.markdown("""
    - **対象**: 中央競馬（JRA）のみ・過去5年・平地競走・未勝利戦以上（新馬戦除外）
    - **ロジック3階層**: ①レース要件（Scope） ②Must（除外条件） ③Prefer/Avoid（順位付け）
    - **二車線**: シミュレーション可能ロジック → 過去5年バックテスト / 不可ロジック → フォワード成績のみ記録
    """)

    # ワークフロー図
    st.subheader("ロジック作成フロー")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        st.markdown("**STEP 1**")
        st.markdown("レース要件（Scope）")
        st.caption("対象レースの条件を定義")
    with col_f2:
        st.markdown("**STEP 2**")
        st.markdown("Must（除外条件）")
        st.caption("最低条件を満たさない馬を除外")
    with col_f3:
        st.markdown("**STEP 3**")
        st.markdown("Prefer / Avoid")
        st.caption("残った馬を順位付け")
    with col_f4:
        st.markdown("**STEP 4**")
        st.markdown("検証")
        st.caption("バックテスト or フォワード成績")

    st.divider()
    st.subheader("プラン比較")
    plan_col1, plan_col2 = st.columns(2)
    with plan_col1:
        st.markdown("**無料プラン**")
        st.markdown("- ロジック記録・編集")
        st.markdown("- フォワード成績記録")
        st.markdown("- 他人の公開ロジック閲覧")
        st.markdown("- 他人のロジックのバックテスト（3回まで）")
    with plan_col2:
        st.markdown("**有料プラン**")
        st.markdown("- 無料プランの全機能")
        st.markdown("- 自分のロジックのバックテスト（無制限）")
        st.markdown("- 他人のロジックのバックテスト（無制限）")

elif nav == "レース要件（Scope）":
    st.header("① レース要件（Scope）")
    st.markdown("対象レースを定義する条件。必須入力・ブロック間はAND・同一カテゴリ内のみOR可。")
    c1, c2 = st.columns(2)
    with c1:
        venues = st.multiselect("競馬場", VENUES, default=VENUES[:1])
        distances = st.multiselect("距離", DISTANCE_CATEGORIES, default=DISTANCE_CATEGORIES[:1])
        surface = st.multiselect("芝／ダート", SURFACE_TYPES, default=SURFACE_TYPES[:1])
    with c2:
        race_class = st.multiselect("クラス", RACE_CLASSES, default=RACE_CLASSES[:1])
        age = st.multiselect("年齢条件", AGE_CONDITIONS, default=AGE_CONDITIONS[:1])
    logic_name = st.text_input("ロジック名（保存時）", value="", placeholder="例: 東京芝1600")
    col_v, col_s = st.columns(2)
    with col_v:
        if st.button("Scope を検証"):
            ok = all([venues, distances, surface, race_class, age])
            if ok:
                st.success("必須項目はすべて選択されています。")
            else:
                st.warning("各カテゴリで1つ以上選択してください。")
    with col_s:
        if st.button("Scope をロジックに保存"):
            if not all([venues, distances, surface, race_class, age]):
                st.warning("各カテゴリで1つ以上選択してから保存してください。")
            elif not logic_name.strip():
                st.warning("ロジック名を入力してください。")
            else:
                try:
                    from models.scope import RaceScope
                    from logic_store import save_scope, list_names
                    scope = RaceScope(venues=venues, distances=distances, surface=surface, race_class=race_class, age_condition=age)
                    save_scope(logic_name.strip(), scope, owner=st.session_state.get("auth_user", ""))
                    st.success(f"「{logic_name.strip()}」を保存しました。")
                except Exception as e:
                    st.error(f"保存に失敗しました: {e}")
    try:
        from logic_store import list_names
        names = list_names(owner=st.session_state.get("auth_user", ""))
        if names:
            st.subheader("保存済みロジック")
            st.write(", ".join(names))
    except Exception:
        pass

elif nav == "予想ロジック Must":
    st.header("② 予想ロジック Must")
    st.markdown("ロジックが成立する最低条件。満たさない馬は除外。**ブロック間はAND**・**同一ブロック内はOR**可。")
    st.markdown("**使用可能データ**: 前走着順, 前走4角位置, 前走距離, 斤量, 枠番／馬番, 最終オッズ帯, 血統指標")
    try:
        from logic_store import list_names, load_must, save_must, load_all as _load_all_must
        from models.must import MustLogic, MustBlock, MUST_CATEGORIES_LIST, MUST_OPERATORS
        from simulation import check_simulatable as _check_sim_must
        names = list_names(owner=st.session_state.get("auth_user", ""))
        if not names:
            st.warning("先に「レース要件（Scope）」でロジックを保存してください。")
        else:
            selected = st.selectbox("対象ロジック", names, key="must_logic_name")
            # シミュレーション可否バッジ
            _all_logics_must = _load_all_must()
            _rec_must = next((r for r in _all_logics_must if r.get("name") == selected), None)
            if _rec_must:
                _can_sim, _sim_reason = _check_sim_must(_rec_must)
                if _can_sim:
                    st.success("このロジックはシミュレーション可能です")
                else:
                    st.warning(f"シミュレーション不可（{_sim_reason}）")
            if st.session_state.get("must_selected_name") != selected:
                loaded = load_must(selected) if selected else None
                st.session_state.must_blocks = (
                    [list(b.conditions) for b in loaded.blocks] if loaded and loaded.blocks else [[]]
                )
                st.session_state.must_selected_name = selected
            if "must_blocks" not in st.session_state:
                st.session_state.must_blocks = [[]]
            blocks = st.session_state.get("must_blocks", [[]])
            for i in range(len(blocks)):
                block_conditions = blocks[i] if isinstance(blocks[i], list) else []
                with st.expander(f"ブロック {i + 1}（ブロック間はAND）", expanded=True):
                    for j in range(len(block_conditions)):
                        cond = block_conditions[j] if isinstance(block_conditions[j], dict) else {}
                        c1, c2, c3, c4 = st.columns([2, 1, 2, 0.5])
                        with c1:
                            cat = st.selectbox(
                                "項目", MUST_CATEGORIES_LIST,
                                index=MUST_CATEGORIES_LIST.index(cond.get("category", MUST_CATEGORIES_LIST[0])) if cond.get("category") in MUST_CATEGORIES_LIST else 0,
                                key=f"must_cat_{i}_{j}",
                            )
                        with c2:
                            op_default = cond.get("operator", "eq")
                            op_idx = next((k for k, o in enumerate(MUST_OPERATORS) if o[1] == op_default), 0)
                            op_label = st.selectbox("演算", [o[0] for o in MUST_OPERATORS], index=op_idx, key=f"must_op_{i}_{j}")
                            op = next(o[1] for o in MUST_OPERATORS if o[0] == op_label)
                        with c3:
                            val = st.text_input("値", value=str(cond.get("value", "")), key=f"must_val_{i}_{j}")
                        with c4:
                            if st.button("削除", key=f"must_del_{i}_{j}"):
                                blocks[i].pop(j)
                                st.session_state.must_blocks = blocks
                                st.rerun()
                        blocks[i][j] = {"category": cat, "operator": op, "value": val}
                    if st.button("条件を追加（このブロック内はOR）", key=f"must_add_cond_{i}"):
                        blocks[i].append({"category": MUST_CATEGORIES_LIST[0], "operator": "eq", "value": ""})
                        st.session_state.must_blocks = blocks
                        st.rerun()
                if st.button("ブロック削除", key=f"must_del_block_{i}"):
                    blocks.pop(i)
                    st.session_state.must_blocks = blocks
                    st.rerun()
                    break
            c_save, c_add_block, c_reset = st.columns(3)
            with c_add_block:
                if st.button("ブロックを追加"):
                    blocks.append([])
                    st.session_state.must_blocks = blocks
                    st.rerun()
            with c_reset:
                if st.button("読み直し"):
                    loaded = load_must(selected) if selected else None
                    st.session_state.must_blocks = (
                        [list(b.conditions) for b in loaded.blocks] if loaded and loaded.blocks else [[]]
                    )
                    st.rerun()
            with c_save:
                if st.button("Must を保存") and selected:
                    must_blocks = st.session_state.get("must_blocks", [[]])
                    logic_blocks = []
                    for b in must_blocks:
                        conds = [c for c in (b if isinstance(b, list) else []) if isinstance(c, dict) and c.get("category")]
                        if conds:
                            logic_blocks.append(MustBlock(conditions=conds))
                    if logic_blocks:
                        save_must(selected, MustLogic(blocks=logic_blocks))
                        st.success(f"「{selected}」の Must を保存しました。")
                    else:
                        st.warning("少なくとも1ブロックに1つ以上の条件を追加してください。")
    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

elif nav == "Prefer / Avoid":
    st.header("③ Prefer / Avoid")
    st.markdown("Must を満たした馬の順位付け。**レキシコグラフィック方式**（段階比較）。加点方式はMVPでは採用しません。")
    st.markdown("- **Prefer**: 最大5個・優先順位・並び替え可能")
    st.markdown("- **Avoid**: 最大2個・順位を下げる条件")
    try:
        from logic_store import list_names, load_prefer_avoid, save_prefer_avoid, load_all as _load_all_pa
        from models.prefer_avoid import PreferAvoidLogic, PreferCondition, AvoidCondition, PREFER_MAX, AVOID_MAX
        from models.must import MUST_CATEGORIES_LIST, MUST_OPERATORS
        from simulation import check_simulatable as _check_sim_pa
        names = list_names(owner=st.session_state.get("auth_user", ""))
        if not names:
            st.warning("先に「レース要件（Scope）」でロジックを保存してください。")
        else:
            selected = st.selectbox("対象ロジック", names, key="pa_logic_name")
            # シミュレーション可否バッジ
            _all_logics_pa = _load_all_pa()
            _rec_pa = next((r for r in _all_logics_pa if r.get("name") == selected), None)
            if _rec_pa:
                _can_sim, _sim_reason = _check_sim_pa(_rec_pa)
                if _can_sim:
                    st.success("このロジックはシミュレーション可能です")
                else:
                    st.warning(f"シミュレーション不可（{_sim_reason}）")
            if st.session_state.get("pa_selected_name") != selected:
                loaded = load_prefer_avoid(selected) if selected else None
                st.session_state.pa_prefer = [p.to_dict() for p in loaded.prefer] if loaded and loaded.prefer else []
                st.session_state.pa_avoid = [a.to_dict() for a in loaded.avoid] if loaded and loaded.avoid else []
                st.session_state.pa_selected_name = selected
            prefer_list = st.session_state.get("pa_prefer", [])
            avoid_list = st.session_state.get("pa_avoid", [])

            st.subheader("Prefer（優先条件・最大5個）")
            for i, p in enumerate(prefer_list):
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 0.5])
                    with c1:
                        name_val = st.text_input("条件名", value=p.get("name", ""), key=f"pa_prefer_name_{i}")
                    with c2:
                        cat = p.get("criteria", {}).get("category", MUST_CATEGORIES_LIST[0])
                        op = p.get("criteria", {}).get("operator", "eq")
                        cat_idx = MUST_CATEGORIES_LIST.index(cat) if cat in MUST_CATEGORIES_LIST else 0
                        op_idx = next((k for k, o in enumerate(MUST_OPERATORS) if o[1] == op), 0)
                        cat_new = st.selectbox("項目", MUST_CATEGORIES_LIST, index=cat_idx, key=f"pa_prefer_cat_{i}")
                        op_label = st.selectbox("演算", [o[0] for o in MUST_OPERATORS], index=op_idx, key=f"pa_prefer_op_{i}")
                        op_new = next(o[1] for o in MUST_OPERATORS if o[0] == op_label)
                        val_new = st.text_input("値", value=str(p.get("criteria", {}).get("value", "")), key=f"pa_prefer_val_{i}")
                    with c3:
                        if st.button("削除", key=f"pa_prefer_del_{i}"):
                            prefer_list.pop(i)
                            st.session_state.pa_prefer = prefer_list
                            st.rerun()
                    prefer_list[i] = {"order": i + 1, "name": name_val, "criteria": {"category": cat_new, "operator": op_new, "value": val_new}}
                    if i > 0 and st.button("↑", key=f"pa_prefer_up_{i}"):
                        prefer_list[i], prefer_list[i - 1] = prefer_list[i - 1], prefer_list[i]
                        for j in range(len(prefer_list)):
                            prefer_list[j]["order"] = j + 1
                        st.session_state.pa_prefer = prefer_list
                        st.rerun()
            if len(prefer_list) < PREFER_MAX and st.button("Prefer を追加"):
                prefer_list.append({"order": len(prefer_list) + 1, "name": "", "criteria": {"category": MUST_CATEGORIES_LIST[0], "operator": "eq", "value": ""}})
                st.session_state.pa_prefer = prefer_list
                st.rerun()

            st.subheader("Avoid（避けたい条件・最大2個）")
            for i, a in enumerate(avoid_list):
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 0.5])
                    with c1:
                        name_val = st.text_input("条件名", value=a.get("name", ""), key=f"pa_avoid_name_{i}")
                    with c2:
                        cat = a.get("criteria", {}).get("category", MUST_CATEGORIES_LIST[0])
                        op = a.get("criteria", {}).get("operator", "eq")
                        cat_idx = MUST_CATEGORIES_LIST.index(cat) if cat in MUST_CATEGORIES_LIST else 0
                        op_idx = next((k for k, o in enumerate(MUST_OPERATORS) if o[1] == op), 0)
                        cat_new = st.selectbox("項目", MUST_CATEGORIES_LIST, index=cat_idx, key=f"pa_avoid_cat_{i}")
                        op_label = st.selectbox("演算", [o[0] for o in MUST_OPERATORS], index=op_idx, key=f"pa_avoid_op_{i}")
                        op_new = next(o[1] for o in MUST_OPERATORS if o[0] == op_label)
                        val_new = st.text_input("値", value=str(a.get("criteria", {}).get("value", "")), key=f"pa_avoid_val_{i}")
                    with c3:
                        if st.button("削除", key=f"pa_avoid_del_{i}"):
                            avoid_list.pop(i)
                            st.session_state.pa_avoid = avoid_list
                            st.rerun()
                    avoid_list[i] = {"name": name_val, "criteria": {"category": cat_new, "operator": op_new, "value": val_new}}
            if len(avoid_list) < AVOID_MAX and st.button("Avoid を追加"):
                avoid_list.append({"name": "", "criteria": {"category": MUST_CATEGORIES_LIST[0], "operator": "eq", "value": ""}})
                st.session_state.pa_avoid = avoid_list
                st.rerun()

            if st.button("Prefer / Avoid を保存") and selected:
                # バリデーション: 空の条件名・値がないかチェック
                validation_errors = []
                for idx, p in enumerate(prefer_list):
                    if not p.get("name", "").strip():
                        validation_errors.append(f"Prefer {idx + 1}: 条件名が未入力です")
                    if not str(p.get("criteria", {}).get("value", "")).strip():
                        validation_errors.append(f"Prefer {idx + 1}: 値が未入力です")
                for idx, a in enumerate(avoid_list):
                    if not a.get("name", "").strip():
                        validation_errors.append(f"Avoid {idx + 1}: 条件名が未入力です")
                    if not str(a.get("criteria", {}).get("value", "")).strip():
                        validation_errors.append(f"Avoid {idx + 1}: 値が未入力です")
                if validation_errors:
                    for err in validation_errors:
                        st.warning(err)
                elif not prefer_list and not avoid_list:
                    st.warning("Prefer または Avoid を1つ以上追加してください。")
                else:
                    prefer_objs = [PreferCondition.from_dict(p) for p in prefer_list]
                    avoid_objs = [AvoidCondition.from_dict(a) for a in avoid_list]
                    pa = PreferAvoidLogic(prefer=prefer_objs, avoid=avoid_objs)
                    save_prefer_avoid(selected, pa)
                    st.success(f"「{selected}」の Prefer / Avoid を保存しました。")
    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

elif nav == "カスタム変数":
    st.header("カスタム変数")
    st.markdown("ユーザー独自の変数を最大3個まで定義できます。**カスタム変数を含むロジックはシミュレーション不可**になります。")
    st.markdown("- **型**: 真偽値 / 3段階カテゴリ（高・中・低） / 数値")
    try:
        from logic_store import list_names, load_custom_vars, save_custom_vars, load_all as _load_all_cv
        from models.custom_variable import (
            CustomVariable, CustomVariableSet, CustomVarType,
            CUSTOM_VAR_MAX, CUSTOM_VAR_TYPE_LIST, THREE_LEVEL_OPTIONS,
        )
        from simulation import check_simulatable as _check_sim_cv
        names = list_names(owner=st.session_state.get("auth_user", ""))
        if not names:
            st.warning("先に「レース要件（Scope）」でロジックを保存してください。")
        else:
            selected = st.selectbox("対象ロジック", names, key="cv_logic_name")
            # シミュレーション可否バッジ
            _all_logics_cv = _load_all_cv()
            _rec_cv = next((r for r in _all_logics_cv if r.get("name") == selected), None)
            if _rec_cv:
                _can_sim, _sim_reason = _check_sim_cv(_rec_cv)
                if _can_sim:
                    st.success("このロジックはシミュレーション可能です")
                else:
                    st.warning(f"シミュレーション不可（{_sim_reason}）")
            # ロジック切替時にセッション状態を同期
            if st.session_state.get("cv_selected_name") != selected:
                loaded = load_custom_vars(selected) if selected else None
                st.session_state.cv_vars = [v.to_dict() for v in loaded.variables] if loaded and loaded.variables else []
                st.session_state.cv_selected_name = selected
            cv_list = st.session_state.get("cv_vars", [])

            for i, v in enumerate(cv_list):
                with st.expander(f"変数 {i + 1}: {v.get('name', '（未設定）')}", expanded=True):
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 0.5])
                    with c1:
                        var_name = st.text_input("変数名", value=v.get("name", ""), key=f"cv_name_{i}")
                    with c2:
                        vt_str = v.get("var_type", CUSTOM_VAR_TYPE_LIST[0])
                        vt_idx = CUSTOM_VAR_TYPE_LIST.index(vt_str) if vt_str in CUSTOM_VAR_TYPE_LIST else 0
                        var_type = st.selectbox("型", CUSTOM_VAR_TYPE_LIST, index=vt_idx, key=f"cv_type_{i}")
                    with c3:
                        # 型に応じたデフォルト値入力
                        if var_type == CustomVarType.BOOLEAN.value:
                            default_val = st.checkbox(
                                "デフォルト値（True/False）",
                                value=bool(v.get("default_value", False)),
                                key=f"cv_default_{i}",
                            )
                        elif var_type == CustomVarType.THREE_LEVEL.value:
                            current_default = v.get("default_value", THREE_LEVEL_OPTIONS[0])
                            tl_idx = THREE_LEVEL_OPTIONS.index(current_default) if current_default in THREE_LEVEL_OPTIONS else 0
                            default_val = st.selectbox(
                                "デフォルト値", THREE_LEVEL_OPTIONS, index=tl_idx, key=f"cv_default_{i}",
                            )
                        else:
                            default_val = st.text_input(
                                "デフォルト値（数値）",
                                value=str(v.get("default_value", "")),
                                key=f"cv_default_{i}",
                            )
                    with c4:
                        if st.button("削除", key=f"cv_del_{i}"):
                            cv_list.pop(i)
                            st.session_state.cv_vars = cv_list
                            st.rerun()
                    cv_list[i] = {"name": var_name, "var_type": var_type, "default_value": default_val}

            if len(cv_list) < CUSTOM_VAR_MAX and st.button("カスタム変数を追加"):
                cv_list.append({"name": "", "var_type": CUSTOM_VAR_TYPE_LIST[0], "default_value": False})
                st.session_state.cv_vars = cv_list
                st.rerun()

            c_save, c_reset, c_clear = st.columns(3)
            with c_save:
                if st.button("カスタム変数を保存") and selected:
                    # バリデーション
                    validation_errors = []
                    seen_names = set()
                    for idx, v in enumerate(cv_list):
                        vname = v.get("name", "").strip()
                        if not vname:
                            validation_errors.append(f"変数 {idx + 1}: 変数名が未入力です")
                        elif vname in seen_names:
                            validation_errors.append(f"変数 {idx + 1}: 変数名「{vname}」が重複しています")
                        seen_names.add(vname)
                        # 数値型のデフォルト値チェック
                        if v.get("var_type") == CustomVarType.NUMERIC.value:
                            dv = str(v.get("default_value", "")).strip()
                            if dv:
                                try:
                                    float(dv)
                                except ValueError:
                                    validation_errors.append(f"変数 {idx + 1}: デフォルト値が数値ではありません")
                    if validation_errors:
                        for err in validation_errors:
                            st.warning(err)
                    else:
                        # 数値型のデフォルト値を変換
                        vars_objs = []
                        for v in cv_list:
                            vt = next((t for t in CustomVarType if t.value == v["var_type"]), CustomVarType.BOOLEAN)
                            dv = v.get("default_value")
                            if vt == CustomVarType.NUMERIC and dv is not None:
                                dv_str = str(dv).strip()
                                dv = float(dv_str) if dv_str else None
                            vars_objs.append(CustomVariable(name=v["name"].strip(), var_type=vt, default_value=dv))
                        cv_set = CustomVariableSet(variables=vars_objs)
                        save_custom_vars(selected, cv_set)
                        st.success(f"「{selected}」のカスタム変数を保存しました。")
            with c_reset:
                if st.button("読み直し"):
                    loaded = load_custom_vars(selected) if selected else None
                    st.session_state.cv_vars = [v.to_dict() for v in loaded.variables] if loaded and loaded.variables else []
                    st.rerun()
            with c_clear:
                if st.button("すべてクリア"):
                    st.session_state.cv_vars = []
                    st.rerun()

            if cv_list:
                st.info("カスタム変数を含むロジックはシミュレーション不可になります。")
    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

elif nav == "ロジック一覧":
    st.header("ロジック一覧・詳細")
    st.markdown("保存済みロジックの確認・削除ができます。各セクションの編集は左メニューの該当画面から行ってください。")
    try:
        from logic_store import load_all, delete_logic, set_public
        from simulation import check_simulatable
        _all_logics = load_all()
        # 自分のロジックのみ表示
        _list_user = st.session_state.get("auth_user", "")
        logics = [r for r in _all_logics if r.get("owner", "") == _list_user]
        if not logics:
            st.info("保存済みのロジックがありません。「レース要件（Scope）」から作成してください。")
        else:
            # サマリテーブル
            _summary_rows = []
            for _r in logics:
                _can, _reason = check_simulatable(_r)
                _has_must = bool(_r.get("must") and _r["must"].get("blocks"))
                _has_pa = bool(_r.get("prefer_avoid") and (_r["prefer_avoid"].get("prefer") or _r["prefer_avoid"].get("avoid")))
                _has_cv = bool(_r.get("custom_vars") and _r["custom_vars"].get("variables"))
                _summary_rows.append({
                    "ロジック名": _r.get("name", ""),
                    "Scope": "設定済" if _r.get("scope") else "未設定",
                    "Must": "設定済" if _has_must else "未設定",
                    "Prefer/Avoid": "設定済" if _has_pa else "未設定",
                    "カスタム変数": "あり" if _has_cv else "なし",
                    "シミュレーション": "可能" if _can else "不可",
                    "公開": "公開" if _r.get("is_public") else "非公開",
                })
            import pandas as pd
            st.dataframe(
                pd.DataFrame(_summary_rows),
                use_container_width=True, hide_index=True,
            )
            st.divider()

            # ロジック選択
            logic_names = [r.get("name", "") for r in logics if r.get("name")]
            selected = st.selectbox("ロジックを選択", logic_names, key="list_logic_name")
            rec = next((r for r in logics if r.get("name") == selected), None)

            if rec:
                # シミュレーション可否
                can_sim, reason = check_simulatable(rec)
                if can_sim:
                    st.success("シミュレーション可能")
                else:
                    st.error(f"シミュレーション不可（{reason}）")

                # 公開/非公開トグル
                current_public = rec.get("is_public", False)
                new_public = st.toggle(
                    "このロジックを公開する",
                    value=current_public,
                    key="list_public_toggle",
                )
                if new_public != current_public:
                    set_public(selected, new_public)
                    label = "公開" if new_public else "非公開"
                    st.success(f"「{selected}」を{label}に設定しました。")
                    st.rerun()

                # Scope 詳細
                st.subheader("Scope（レース要件）")
                scope = rec.get("scope")
                if scope:
                    scope_cols = st.columns(5)
                    labels = ["競馬場", "距離", "芝/ダート", "クラス", "年齢条件"]
                    keys = ["venues", "distances", "surface", "race_class", "age_condition"]
                    for col, label, key in zip(scope_cols, labels, keys):
                        with col:
                            vals = scope.get(key, [])
                            st.markdown(f"**{label}**")
                            st.write(", ".join(vals) if vals else "（未設定）")
                else:
                    st.write("（未設定）")

                # Must 詳細
                st.subheader("Must（除外条件）")
                must = rec.get("must")
                if must and must.get("blocks"):
                    for bi, block in enumerate(must["blocks"]):
                        conds = block.get("conditions", [])
                        if conds:
                            cond_strs = []
                            for c in conds:
                                op_map = OP_DISPLAY_MAP
                                op_label = op_map.get(c.get("operator", ""), c.get("operator", ""))
                                cond_strs.append(f"{c.get('category', '')} {op_label} {c.get('value', '')}")
                            st.markdown(f"**ブロック {bi + 1}** (OR): " + " / ".join(cond_strs))
                    st.caption("ブロック間は AND で結合")
                else:
                    st.write("（未設定）")

                # Prefer/Avoid 詳細
                st.subheader("Prefer / Avoid")
                pa = rec.get("prefer_avoid")
                if pa:
                    prefer = pa.get("prefer", [])
                    avoid = pa.get("avoid", [])
                    if prefer:
                        st.markdown("**Prefer（優先条件）**")
                        for p in sorted(prefer, key=lambda x: x.get("order", 999)):
                            cr = p.get("criteria", {})
                            op_map = OP_DISPLAY_MAP
                            op_label = op_map.get(cr.get("operator", ""), cr.get("operator", ""))
                            st.write(f"  {p.get('order', '?')}. {p.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
                    if avoid:
                        st.markdown("**Avoid（回避条件）**")
                        for a in avoid:
                            cr = a.get("criteria", {})
                            op_map = OP_DISPLAY_MAP
                            op_label = op_map.get(cr.get("operator", ""), cr.get("operator", ""))
                            st.write(f"  - {a.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
                    if not prefer and not avoid:
                        st.write("（未設定）")
                else:
                    st.write("（未設定）")

                # カスタム変数 詳細
                st.subheader("カスタム変数")
                cv = rec.get("custom_vars")
                if cv and cv.get("variables"):
                    for vi, v in enumerate(cv["variables"]):
                        dv = v.get("default_value", "")
                        dv_str = f"（デフォルト: {dv}）" if dv is not None and str(dv) != "" else ""
                        st.write(f"  {vi + 1}. {v.get('name', '')} [{v.get('var_type', '')}] {dv_str}")
                else:
                    st.write("（なし）")

                # 削除ボタン
                st.divider()
                if st.button("このロジックを削除", type="secondary", key="list_delete_btn"):
                    st.session_state["list_confirm_delete"] = selected

                if st.session_state.get("list_confirm_delete") == selected:
                    st.warning(f"「{selected}」を削除しますか？ この操作は元に戻せません。")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button("削除する", type="primary", key="list_delete_confirm"):
                            if delete_logic(selected):
                                st.session_state.pop("list_confirm_delete", None)
                                st.success(f"「{selected}」を削除しました。")
                                st.rerun()
                            else:
                                st.error("削除に失敗しました。")
                    with c_no:
                        if st.button("キャンセル", key="list_delete_cancel"):
                            st.session_state.pop("list_confirm_delete", None)
                            st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

elif nav == "公開ロジック":
    st.header("公開ロジック")
    st.markdown("他のユーザーが公開しているロジックを閲覧できます。無料プランでは回数制限付きでバックテストも実行可能です。")
    try:
        from logic_store import list_public_logics
        from simulation import check_simulatable
        public_logics = list_public_logics()
        current_user = st.session_state.get("auth_user", "")

        # 自分のロジックを除外して表示
        other_logics = [r for r in public_logics if r.get("owner", "") != current_user]
        if not other_logics:
            # 自分のロジックも含めて公開ロジックがなければメッセージ表示
            if not public_logics:
                st.info("現在公開されているロジックはありません。")
            else:
                st.info("他のユーザーの公開ロジックはありません。自分のロジックは「ロジック一覧」から確認できます。")
        else:
            # 公開ロジック一覧
            pub_names = [r.get("name", "") for r in other_logics]
            pub_owners = {r.get("name", ""): r.get("owner", "（不明）") for r in other_logics}
            selected_pub = st.selectbox("公開ロジックを選択", pub_names, key="pub_logic_name")
            pub_rec = next((r for r in other_logics if r.get("name") == selected_pub), None)

            if pub_rec:
                st.caption(f"作成者: {pub_owners.get(selected_pub, '（不明）')}")

                # シミュレーション可否
                can_sim, reason = check_simulatable(pub_rec)
                if can_sim:
                    st.success("シミュレーション可能")
                else:
                    st.error(f"シミュレーション不可（{reason}）")

                # 公開ロジックのバックテスト実行（回数制限あり）
                if can_sim:
                    st.divider()
                    st.subheader("バックテスト実行")
                    from models.simulation_spec import BetType as _PubBetType
                    from simulation import run_backtest as _pub_run_backtest
                    from auth_store import can_run_backtest as _pub_can_run, increment_backtest_count as _pub_inc

                    _pub_bet_label = st.radio(
                        "券種", ["単勝", "複勝"], horizontal=True, key="pub_bet_type",
                    )
                    _pub_bet_type = _PubBetType.WIN if _pub_bet_label == "単勝" else _PubBetType.PLACE

                    if st.button("バックテストを実行", key="pub_sim_run"):
                        _pub_can, _pub_msg = _pub_can_run(current_user, is_own_logic=False)
                        if not _pub_can:
                            st.warning(_pub_msg)
                        else:
                            if _pub_msg:
                                st.info(_pub_msg)
                            try:
                                with st.spinner("バックテスト実行中..."):
                                    _pub_result = _pub_run_backtest(pub_rec, _pub_bet_type)
                            except ValueError as ve:
                                st.error(f"バックテスト実行エラー: {ve}")
                                st.stop()
                            _pub_inc(current_user)

                            # 結果表示
                            st.subheader("バックテスト結果")
                            _pc1, _pc2, _pc3 = st.columns(3)
                            with _pc1:
                                st.metric("試行回数", f"{_pub_result['試行回数']} 回")
                            with _pc2:
                                st.metric("回収率", f"{_pub_result['回収率']}%")
                            with _pc3:
                                st.metric("的中率", f"{_pub_result['的中率']}%")

                            _pc4, _pc5 = st.columns(2)
                            with _pc4:
                                st.metric("最大ドローダウン", f"{_pub_result['最大ドローダウン']:,.0f} 円")
                            with _pc5:
                                st.metric("最大連敗数", f"{_pub_result['最大連敗数']} 連敗")

                            _pub_yearly = _pub_result.get("年別推移", [])
                            if _pub_yearly:
                                st.subheader("年別推移")
                                import pandas as pd
                                _pub_df = pd.DataFrame(_pub_yearly)
                                _pub_df = _pub_df.rename(columns={"年": "年度", "試行回数": "試行", "的中率": "的中率(%)", "回収率": "回収率(%)"})
                                st.dataframe(_pub_df, use_container_width=True, hide_index=True)
                    st.divider()

                # Scope 詳細
                st.subheader("Scope（レース要件）")
                scope = pub_rec.get("scope")
                if scope:
                    scope_cols = st.columns(5)
                    labels = ["競馬場", "距離", "芝/ダート", "クラス", "年齢条件"]
                    keys = ["venues", "distances", "surface", "race_class", "age_condition"]
                    for col, label, key in zip(scope_cols, labels, keys):
                        with col:
                            vals = scope.get(key, [])
                            st.markdown(f"**{label}**")
                            st.write(", ".join(vals) if vals else "（未設定）")
                else:
                    st.write("（未設定）")

                # Must 詳細
                st.subheader("Must（除外条件）")
                must = pub_rec.get("must")
                if must and must.get("blocks"):
                    for bi, block in enumerate(must["blocks"]):
                        conds = block.get("conditions", [])
                        if conds:
                            cond_strs = []
                            for c in conds:
                                op_map = OP_DISPLAY_MAP
                                op_label = op_map.get(c.get("operator", ""), c.get("operator", ""))
                                cond_strs.append(f"{c.get('category', '')} {op_label} {c.get('value', '')}")
                            st.markdown(f"**ブロック {bi + 1}** (OR): " + " / ".join(cond_strs))
                    st.caption("ブロック間は AND で結合")
                else:
                    st.write("（未設定）")

                # Prefer/Avoid 詳細
                st.subheader("Prefer / Avoid")
                pa = pub_rec.get("prefer_avoid")
                if pa:
                    prefer = pa.get("prefer", [])
                    avoid = pa.get("avoid", [])
                    if prefer:
                        st.markdown("**Prefer（優先条件）**")
                        for p in sorted(prefer, key=lambda x: x.get("order", 999)):
                            cr = p.get("criteria", {})
                            op_map = OP_DISPLAY_MAP
                            op_label = op_map.get(cr.get("operator", ""), cr.get("operator", ""))
                            st.write(f"  {p.get('order', '?')}. {p.get('name', '')} -- {cr.get('category', '')} {op_label} {cr.get('value', '')}")
                    if avoid:
                        st.markdown("**Avoid（回避条件）**")
                        for a in avoid:
                            cr = a.get("criteria", {})
                            op_map = OP_DISPLAY_MAP
                            op_label = op_map.get(cr.get("operator", ""), cr.get("operator", ""))
                            st.write(f"  - {a.get('name', '')} -- {cr.get('category', '')} {op_label} {cr.get('value', '')}")
                    if not prefer and not avoid:
                        st.write("（未設定）")
                else:
                    st.write("（未設定）")
    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

elif nav == "フォワード成績":
    st.header("フォワード成績")
    st.markdown("実運用での予想結果（的中/不的中・払戻金額）を記録・確認できます。**無料機能**です。")
    try:
        from logic_store import (
            list_names, load_forward_record, save_forward_result, delete_forward_result,
        )
        from models.forward_record import ForwardResult
        names = list_names(owner=st.session_state.get("auth_user", ""))
        if not names:
            st.warning("先に「レース要件（Scope）」でロジックを保存してください。")
        else:
            selected = st.selectbox("対象ロジック", names, key="fw_logic_name")

            # 成績サマリ
            record = load_forward_record(selected)
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

                # 成績一覧テーブル
                st.subheader("成績一覧")
                for i, r in enumerate(reversed(record.results)):
                    idx = len(record.results) - 1 - i  # 実際のインデックス
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
                            delete_forward_result(selected, idx)
                            st.rerun()
            else:
                st.info("まだ成績が記録されていません。下のフォームから記録を追加してください。")

            # 新規記録フォーム
            st.divider()
            st.subheader("成績を記録")
            with st.form("fw_add_form", clear_on_submit=True):
                fc1, fc2 = st.columns(2)
                with fc1:
                    race_id = st.text_input("レースID", placeholder="例: 202501010101")
                    race_date = st.date_input("レース日")
                    race_name = st.text_input("レース名", placeholder="例: 東京5R")
                    bet_type = st.selectbox("券種", ["単勝", "複勝"])
                with fc2:
                    horse_name = st.text_input("予想馬名", placeholder="例: サンプルホース")
                    horse_number = st.number_input("馬番", min_value=1, max_value=18, value=1)
                    bet_amount = st.number_input("賭け金（円）", min_value=100, value=100, step=100)
                    is_hit = st.checkbox("的中した")
                    payout = st.number_input("払戻金額（円）", min_value=0, value=0, step=10)

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
                        save_forward_result(selected, result)
                        st.success("成績を記録しました。")
                        st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

elif nav == "シミュレーション":
    st.header("シミュレーション")
    st.markdown("**対象**: シミュレーション可能ロジックのみ（完全選択式・内部データのみ・カスタム変数なし）")
    st.markdown("- 券種: 単勝・複勝 │ 賭け金: 100円換算 │ オッズ: 発走直前最終オッズに固定")
    st.markdown("**出力**: 試行回数, 回収率, 的中率, 年別推移, 最大ドローダウン, 最大連敗数")
    st.warning("バックテスト実行は有料機能です。ロジックを記録したうえでシミュレーション可能かどうかが自動判定されます。")

    # ロジック一覧とシミュレーション可否バッジ・バックテスト実行
    try:
        from logic_store import load_all
        from simulation import check_simulatable, run_backtest, get_logic_type_info
        from models.simulation_spec import BetType

        _all_logics_sim = load_all()
        # 自分のロジックのみ表示
        _sim_user = st.session_state.get("auth_user", "")
        logics = [r for r in _all_logics_sim if r.get("owner", "") == _sim_user]
        if not logics:
            st.info("保存済みのロジックがありません。先に「レース要件（Scope）」からロジックを作成してください。")
        else:
            st.subheader("ロジック一覧・シミュレーション可否")
            # シミュレーション可能なロジック名を収集
            simulatable_names = []
            for rec in logics:
                name = rec.get("name", "（名前なし）")
                info = get_logic_type_info(rec)
                if info["can_simulate"]:
                    st.success(f"**{name}** — {info['logic_type']}")
                    st.caption(info["description"])
                    simulatable_names.append(name)
                else:
                    st.error(f"**{name}** — {info['logic_type']}")
                    st.caption(info["description"])

            # バックテスト実行UI（有料機能）
            if simulatable_names:
                st.divider()
                st.subheader("バックテスト実行")
                st.info("バックテスト実行は**有料機能**です。無料プランではロジック記録・フォワード成績表示のみ利用可能です。")

                selected_logic = st.selectbox(
                    "対象ロジック（シミュレーション可能のみ）",
                    simulatable_names,
                    key="sim_target_logic",
                )
                bet_type_label = st.radio(
                    "券種", ["単勝", "複勝"], horizontal=True, key="sim_bet_type",
                )
                bet_type = BetType.WIN if bet_type_label == "単勝" else BetType.PLACE

                if st.button("バックテストを実行（有料）", key="sim_run"):
                    # 有料機能ゲート: ユーザーのプランに応じて実行可否を判定
                    from auth_store import can_run_backtest, increment_backtest_count
                    current_user = st.session_state.get("auth_user", "")
                    # 対象ロジックレコードを取得
                    target_rec = next(
                        (r for r in logics if r.get("name") == selected_logic), None
                    )
                    # ロジックのオーナー判定（MVP: ロジックに owner フィールドがない場合は自分のものとみなす）
                    is_own = target_rec.get("owner", current_user) == current_user if target_rec else True
                    can_run, plan_msg = can_run_backtest(current_user, is_own)
                    if not can_run:
                        st.warning(plan_msg)
                    elif target_rec is None:
                        st.error("ロジックが見つかりません。")
                    else:
                        if plan_msg:
                            st.info(plan_msg)
                        try:
                            with st.spinner("バックテスト実行中..."):
                                result = run_backtest(target_rec, bet_type)
                        except ValueError as ve:
                            st.error(f"バックテスト実行エラー: {ve}")
                            st.stop()
                        # 他人のロジックの場合、無料ユーザーのバックテスト回数をカウント
                        if not is_own:
                            increment_backtest_count(current_user)

                        # 結果表示
                        st.subheader("バックテスト結果")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.metric("試行回数", f"{result['試行回数']} 回")
                        with c2:
                            st.metric("回収率", f"{result['回収率']}%")
                        with c3:
                            st.metric("的中率", f"{result['的中率']}%")

                        c4, c5 = st.columns(2)
                        with c4:
                            st.metric("最大ドローダウン", f"{result['最大ドローダウン']:,.0f} 円")
                        with c5:
                            st.metric("最大連敗数", f"{result['最大連敗数']} 連敗")

                        # 年別推移
                        yearly = result.get("年別推移", [])
                        if yearly:
                            st.subheader("年別推移")
                            import pandas as pd
                            df = pd.DataFrame(yearly)
                            df = df.rename(columns={"年": "年度", "試行回数": "試行", "的中率": "的中率(%)", "回収率": "回収率(%)"})
                            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"エラー: {e}")
        import traceback
        st.code(traceback.format_exc())

elif nav == "仕様書":
    st.header("MVP 要件定義")
    # docs/MVP_SPEC.md を読み込んで表示
    _spec_path = Path(__file__).resolve().parent.parent / "docs" / "MVP_SPEC.md"
    if _spec_path.exists():
        st.markdown(_spec_path.read_text(encoding="utf-8"))
    else:
        st.markdown("""
    - 対象範囲: 中央競馬・過去5年・平地・未勝利戦以上
    - ロジック3階層: Scope / Must / Prefer-Avoid
    - 血統: 5世代・事前定義指標のみ
    - 導出指標（固定）: 逃げ馬数, 先行馬数, 前走位置平均との差, レースペース（速/普/遅）
    - MVPでやらないこと: 地方競馬, 6年超データ, 血統ツリー自由編集, 重みスコア, AI自動ロジック, 買い目最適化, CSV出力
    """)
