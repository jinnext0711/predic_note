"""
マイロジック一覧 - 保存済みロジックの確認・管理・セクション別インライン編集。
"""
import streamlit as st
from pages.styles import inject_custom_css, show_help

# 定数インポート
from constants.scope_options import (
    VENUES, DISTANCE_MIN, DISTANCE_MAX, DISTANCE_STEP,
    SURFACE_TYPES, RACE_CLASSES, AGE_CONDITIONS,
)
from models.must import MUST_CATEGORIES_LIST, MUST_OPERATORS
from models.prefer_avoid import PREFER_MAX, AVOID_MAX

# 演算子の表示ラベル
OP_DISPLAY_MAP = {"eq": "=", "le": "<=", "ge": ">=", "lt": "<", "gt": ">", "in": "含む"}

# 演算子に日本語説明を付与
OPERATOR_LABELS = {
    "eq": "等しい (=)",
    "le": "以下 (<=)",
    "ge": "以上 (>=)",
    "lt": "未満 (<)",
    "gt": "超える (>)",
    "in": "含む",
}


def _get_operator_labels():
    """MUST_OPERATORSから日本語付きラベルリストを生成"""
    return [(OPERATOR_LABELS.get(code, label), code) for label, code in MUST_OPERATORS]


def _init_edit_state():
    """インライン編集用のセッション状態を初期化"""
    if "mylogic_edit_section" not in st.session_state:
        st.session_state.mylogic_edit_section = None


def _cancel_edit():
    """編集モードをキャンセル"""
    st.session_state.mylogic_edit_section = None
    # 編集用の一時状態をクリア
    keys_to_clear = [k for k in st.session_state if k.startswith("myedit_")]
    for k in keys_to_clear:
        del st.session_state[k]


def render():
    inject_custom_css()
    _init_edit_state()

    st.header("マイロジック")

    try:
        from logic_store import load_all, delete_logic, set_public
        from simulation import check_simulatable

        _all_logics = load_all()
        _list_user = st.session_state.get("auth_user", "")
        logics = [r for r in _all_logics if r.get("owner", "") == _list_user]

        if not logics:
            st.info("まだロジックがありません。")
            show_help(
                "「ロジック作成」ページからロジックを作成してください。"
                "レース条件と馬の条件を設定するだけでOKです。"
            )
            return

        # サマリテーブル
        import pandas as pd
        _summary_rows = []
        for _r in logics:
            _can, _reason = check_simulatable(_r)
            _has_must = bool(_r.get("must") and _r["must"].get("blocks"))
            _has_pa = bool(_r.get("prefer_avoid") and (_r["prefer_avoid"].get("prefer") or _r["prefer_avoid"].get("avoid")))
            _has_cv = bool(_r.get("custom_vars") and _r["custom_vars"].get("variables"))
            _summary_rows.append({
                "ロジック名": _r.get("name", ""),
                "Scope": "✓" if _r.get("scope") else "−",
                "Must": "✓" if _has_must else "−",
                "Prefer/Avoid": "✓" if _has_pa else "−",
                "カスタム変数": "✓" if _has_cv else "−",
                "バックテスト": "可能" if _can else "不可",
                "公開": "公開中" if _r.get("is_public") else "非公開",
            })
        st.dataframe(
            pd.DataFrame(_summary_rows),
            use_container_width=True, hide_index=True,
        )

        st.divider()

        # ロジック詳細
        logic_names = [r.get("name", "") for r in logics if r.get("name")]
        selected = st.selectbox("ロジックを選んで詳細を見る", logic_names, key="mylogic_select")
        rec = next((r for r in logics if r.get("name") == selected), None)

        if rec:
            # シミュレーション可否
            can_sim, reason = check_simulatable(rec)
            if can_sim:
                col_sim, col_go = st.columns([3, 1])
                with col_sim:
                    st.success("バックテスト可能")
                with col_go:
                    if st.button("バックテストへ →", key="mylogic_goto_bt"):
                        st.session_state.nav_page = "バックテスト"
                        st.session_state.bt_logic = selected
                        st.rerun()
            else:
                st.warning(f"バックテスト不可（{reason}）")

            # 公開/非公開トグル
            current_public = rec.get("is_public", False)
            new_public = st.toggle("このロジックを公開する", value=current_public, key="mylogic_public")
            if new_public != current_public:
                set_public(selected, new_public)
                label = "公開" if new_public else "非公開"
                st.success(f"「{selected}」を{label}に設定しました。")
                st.rerun()

            # マーケットプレイス出品ボタン
            _render_marketplace_listing(selected, rec, can_sim, _list_user)

            # 成績サマリ（バックテスト＋フォワード並列）
            _render_performance_summary(selected, rec, can_sim)

            st.divider()

            # セクション別表示＋インライン編集
            _render_section_description(selected, rec)
            _render_section_scope(selected, rec)
            _render_section_must(selected, rec)
            _render_section_prefer_avoid(selected, rec)

            # カスタム変数（既存維持）
            st.divider()
            st.subheader("カスタム変数")
            _render_custom_vars(selected, rec)

            # 削除ボタン
            st.divider()
            if st.button("このロジックを削除", key="mylogic_delete"):
                st.session_state["mylogic_confirm_delete"] = selected

            if st.session_state.get("mylogic_confirm_delete") == selected:
                st.warning(f"「{selected}」を削除しますか？ この操作は元に戻せません。")
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("削除する", type="primary", key="mylogic_delete_yes"):
                        if delete_logic(selected):
                            st.session_state.pop("mylogic_confirm_delete", None)
                            _cancel_edit()
                            st.success(f"「{selected}」を削除しました。")
                            st.rerun()
                with c_no:
                    if st.button("キャンセル", key="mylogic_delete_no"):
                        st.session_state.pop("mylogic_confirm_delete", None)
                        st.rerun()
    except Exception as e:
        st.error("予期しないエラーが発生しました。ページを再読み込みしてください。")
        import logging
        logging.getLogger(__name__).exception("my_logics page error")


# ────────────────────────────────────────────
# セクション別インライン編集
# ────────────────────────────────────────────

def _render_section_description(selected: str, rec: dict):
    """説明文セクション（表示＋インライン編集）"""
    editing = st.session_state.mylogic_edit_section == "description"

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.subheader("説明")
    with col_btn:
        if not editing:
            if st.button("編集", key="mylogic_edit_desc_btn"):
                _cancel_edit()
                st.session_state.mylogic_edit_section = "description"
                st.session_state.myedit_description = rec.get("description", "")
                st.rerun()

    if editing:
        desc = st.text_area(
            "説明文",
            value=st.session_state.get("myedit_description", rec.get("description", "")),
            key="myedit_desc_input",
            height=100,
        )
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("保存", type="primary", key="mylogic_save_desc", use_container_width=True):
                from logic_store import save_description
                save_description(selected, desc.strip())
                _cancel_edit()
                st.success("説明文を保存しました。")
                st.rerun()
        with col_cancel:
            if st.button("キャンセル", key="mylogic_cancel_desc", use_container_width=True):
                _cancel_edit()
                st.rerun()
    else:
        desc = rec.get("description", "")
        st.write(desc if desc else "（未設定）")


def _render_section_scope(selected: str, rec: dict):
    """Scope セクション（表示＋インライン編集）"""
    editing = st.session_state.mylogic_edit_section == "scope"

    st.divider()
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.subheader("レース条件（Scope）")
    with col_btn:
        if not editing:
            if st.button("編集", key="mylogic_edit_scope_btn"):
                _cancel_edit()
                st.session_state.mylogic_edit_section = "scope"
                # 既存のスコープ値を編集用状態にロード
                scope = rec.get("scope", {})
                st.session_state.myedit_venues = scope.get("venues", [])
                st.session_state.myedit_distance_min = scope.get("distance_min", 1000)
                st.session_state.myedit_distance_max = scope.get("distance_max", 1800)
                st.session_state.myedit_surface = scope.get("surface", [])
                st.session_state.myedit_race_class = scope.get("race_class", [])
                st.session_state.myedit_age = scope.get("age_condition", [])
                st.rerun()

    if editing:
        _render_scope_edit_form(selected, rec)
    else:
        _render_scope_display(rec)


def _render_scope_display(rec: dict):
    """Scope の表示のみ"""
    scope = rec.get("scope")
    if scope:
        scope_cols = st.columns(5)
        with scope_cols[0]:
            st.markdown("**距離**")
            d_min = scope.get("distance_min")
            d_max = scope.get("distance_max")
            if d_min is not None and d_max is not None:
                st.write(f"{d_min}m 〜 {d_max}m")
            else:
                st.write("（未設定）")
        labels_keys = [
            ("競馬場", "venues"), ("芝/ダート", "surface"),
            ("クラス", "race_class"), ("年齢条件", "age_condition"),
        ]
        for col, (label, key) in zip(scope_cols[1:], labels_keys):
            with col:
                vals = scope.get(key, [])
                st.markdown(f"**{label}**")
                st.write(", ".join(vals) if vals else "（未設定）")
    else:
        st.write("（未設定）")


def _render_scope_edit_form(selected: str, rec: dict):
    """Scope のインライン編集フォーム"""
    col1, col2 = st.columns(2)
    with col1:
        venues = st.multiselect(
            "競馬場", VENUES,
            help="対象とする競馬場を選択",
            key="myedit_venues",
        )
        st.markdown("**距離（m）**")
        dist_col1, dist_col2 = st.columns(2)
        with dist_col1:
            distance_min = st.number_input(
                "下限",
                min_value=DISTANCE_MIN, max_value=DISTANCE_MAX,
                step=DISTANCE_STEP, key="myedit_distance_min",
            )
        with dist_col2:
            distance_max = st.number_input(
                "上限",
                min_value=DISTANCE_MIN, max_value=DISTANCE_MAX,
                step=DISTANCE_STEP, key="myedit_distance_max",
            )
        surface = st.multiselect(
            "芝 / ダート", SURFACE_TYPES, key="myedit_surface",
        )
    with col2:
        race_class = st.multiselect(
            "クラス", RACE_CLASSES, key="myedit_race_class",
        )
        age = st.multiselect(
            "年齢条件", AGE_CONDITIONS, key="myedit_age",
        )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("保存", type="primary", key="mylogic_save_scope", use_container_width=True):
            # バリデーション
            if not all([venues, surface, race_class, age]):
                st.error("各カテゴリで1つ以上選択してください。")
                return
            if distance_min > distance_max:
                st.error("距離の下限は上限以下にしてください。")
                return
            from logic_store import save_scope
            from models.scope import RaceScope
            owner = st.session_state.get("auth_user", "")
            race_scope = RaceScope(
                venues=venues, surface=surface,
                race_class=race_class, age_condition=age,
                distance_min=distance_min, distance_max=distance_max,
            )
            save_scope(selected, race_scope, owner=owner)
            _cancel_edit()
            st.success("レース条件を保存しました。")
            st.rerun()
    with col_cancel:
        if st.button("キャンセル", key="mylogic_cancel_scope", use_container_width=True):
            _cancel_edit()
            st.rerun()


def _render_section_must(selected: str, rec: dict):
    """Must セクション（表示＋インライン編集）"""
    editing = st.session_state.mylogic_edit_section == "must"

    st.divider()
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.subheader("除外条件（Must）")
    with col_btn:
        if not editing:
            if st.button("編集", key="mylogic_edit_must_btn"):
                _cancel_edit()
                st.session_state.mylogic_edit_section = "must"
                # 既存のMustデータを編集用状態にロード
                must = rec.get("must")
                if must and must.get("blocks"):
                    st.session_state.myedit_must_blocks = [
                        list(b.get("conditions", [])) for b in must["blocks"]
                    ]
                else:
                    st.session_state.myedit_must_blocks = [[]]
                st.rerun()

    if editing:
        _render_must_edit_form(selected)
    else:
        _render_must_display(rec)


def _render_must_display(rec: dict):
    """Must の表示のみ"""
    must = rec.get("must")
    if must and must.get("blocks"):
        for bi, block in enumerate(must["blocks"]):
            conds = block.get("conditions", [])
            if conds:
                cond_strs = []
                for c in conds:
                    op_label = OP_DISPLAY_MAP.get(c.get("operator", ""), c.get("operator", ""))
                    cond_strs.append(f"{c.get('category', '')} {op_label} {c.get('value', '')}")
                st.markdown(f"**グループ {bi + 1}** (OR): " + " / ".join(cond_strs))
        st.caption("グループ間はAND（すべて満たす必要あり）")
    else:
        st.write("（未設定 - すべての馬が対象）")


def _render_must_edit_form(selected: str):
    """Must のインライン編集フォーム"""
    blocks = st.session_state.myedit_must_blocks

    for i in range(len(blocks)):
        block_conditions = blocks[i] if isinstance(blocks[i], list) else []
        with st.expander(f"条件グループ {i + 1}（グループ内はOR = いずれかを満たせばOK）", expanded=True):
            for j in range(len(block_conditions)):
                cond = block_conditions[j] if isinstance(block_conditions[j], dict) else {}
                c1, c2, c3, c4 = st.columns([2, 1, 2, 0.5])
                with c1:
                    cat = st.selectbox(
                        "項目", MUST_CATEGORIES_LIST,
                        index=MUST_CATEGORIES_LIST.index(cond.get("category", MUST_CATEGORIES_LIST[0]))
                        if cond.get("category") in MUST_CATEGORIES_LIST else 0,
                        key=f"myedit_must_cat_{i}_{j}",
                    )
                with c2:
                    op_default = cond.get("operator", "le")
                    jp_operators = _get_operator_labels()
                    op_idx = next((k for k, (_, code) in enumerate(jp_operators) if code == op_default), 0)
                    op_label = st.selectbox(
                        "条件",
                        [label for label, _ in jp_operators],
                        index=op_idx,
                        key=f"myedit_must_op_{i}_{j}",
                    )
                    op = next(code for label, code in jp_operators if label == op_label)
                with c3:
                    val = st.text_input(
                        "値",
                        value=str(cond.get("value", "")),
                        key=f"myedit_must_val_{i}_{j}",
                        placeholder="例: 5",
                    )
                with c4:
                    if st.button("×", key=f"myedit_must_del_{i}_{j}"):
                        blocks[i].pop(j)
                        st.session_state.myedit_must_blocks = blocks
                        st.rerun()
                blocks[i][j] = {"category": cat, "operator": op, "value": val}

            if st.button("+ 条件を追加", key=f"myedit_must_add_{i}"):
                blocks[i].append({"category": MUST_CATEGORIES_LIST[0], "operator": "le", "value": ""})
                st.session_state.myedit_must_blocks = blocks
                st.rerun()

        if len(blocks) > 1 and st.button("このグループを削除", key=f"myedit_must_delblk_{i}"):
            blocks.pop(i)
            st.session_state.myedit_must_blocks = blocks
            st.rerun()
            return

    st.caption("複数グループ間はAND（すべて満たす必要あり）")
    if st.button("+ 条件グループを追加", key="myedit_must_addblk"):
        blocks.append([])
        st.session_state.myedit_must_blocks = blocks
        st.rerun()

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("保存", type="primary", key="mylogic_save_must", use_container_width=True):
            from logic_store import save_must
            from models.must import MustLogic, MustBlock
            logic_blocks = []
            for b in blocks:
                conds = [c for c in (b if isinstance(b, list) else [])
                         if isinstance(c, dict) and c.get("category") and str(c.get("value", "")).strip()]
                if conds:
                    logic_blocks.append(MustBlock(conditions=conds))
            if logic_blocks:
                save_must(selected, MustLogic(blocks=logic_blocks))
            else:
                # 全条件クリアの場合はMustをNoneに
                from logic_store import _save_field
                _save_field(selected, "must", None)
            _cancel_edit()
            st.success("除外条件を保存しました。")
            st.rerun()
    with col_cancel:
        if st.button("キャンセル", key="mylogic_cancel_must", use_container_width=True):
            _cancel_edit()
            st.rerun()


def _render_section_prefer_avoid(selected: str, rec: dict):
    """Prefer/Avoid セクション（表示＋インライン編集）"""
    editing = st.session_state.mylogic_edit_section == "prefer_avoid"

    st.divider()
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.subheader("優先/回避条件（Prefer/Avoid）")
    with col_btn:
        if not editing:
            if st.button("編集", key="mylogic_edit_pa_btn"):
                _cancel_edit()
                st.session_state.mylogic_edit_section = "prefer_avoid"
                # 既存のPrefer/Avoidデータを編集用状態にロード
                pa = rec.get("prefer_avoid")
                if pa:
                    st.session_state.myedit_prefer = list(pa.get("prefer", []))
                    st.session_state.myedit_avoid = list(pa.get("avoid", []))
                else:
                    st.session_state.myedit_prefer = []
                    st.session_state.myedit_avoid = []
                st.rerun()

    if editing:
        _render_prefer_avoid_edit_form(selected)
    else:
        _render_prefer_avoid_display(rec)


def _render_prefer_avoid_display(rec: dict):
    """Prefer/Avoid の表示のみ"""
    pa = rec.get("prefer_avoid")
    if pa:
        prefer = pa.get("prefer", [])
        avoid = pa.get("avoid", [])
        if prefer:
            st.markdown("**優先条件（Prefer）**")
            for p in sorted(prefer, key=lambda x: x.get("order", 999)):
                cr = p.get("criteria", {})
                op_label = OP_DISPLAY_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
                st.write(f"  {p.get('order', '?')}. {p.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
        if avoid:
            st.markdown("**回避条件（Avoid）**")
            for a in avoid:
                cr = a.get("criteria", {})
                op_label = OP_DISPLAY_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
                st.write(f"  - {a.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
        if not prefer and not avoid:
            st.write("（未設定）")
    else:
        st.write("（未設定）")


def _render_prefer_avoid_edit_form(selected: str):
    """Prefer/Avoid のインライン編集フォーム"""
    prefer_list = st.session_state.myedit_prefer
    avoid_list = st.session_state.myedit_avoid

    # Prefer
    st.markdown("#### 優先条件 - 最大5個")
    st.caption("条件を満たす馬ほど上位に。1番目が最も重視されます。")
    for i, p in enumerate(prefer_list):
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 2, 0.5])
            with c1:
                name_val = st.text_input(
                    "条件名", value=p.get("name", ""),
                    key=f"myedit_pref_name_{i}",
                    placeholder="例: 前走好走",
                )
            with c2:
                cat = p.get("criteria", {}).get("category", MUST_CATEGORIES_LIST[0])
                cat_idx = MUST_CATEGORIES_LIST.index(cat) if cat in MUST_CATEGORIES_LIST else 0
                cat_new = st.selectbox("項目", MUST_CATEGORIES_LIST, index=cat_idx, key=f"myedit_pref_cat_{i}")
            with c3:
                op = p.get("criteria", {}).get("operator", "le")
                jp_ops = _get_operator_labels()
                op_idx = next((k for k, (_, code) in enumerate(jp_ops) if code == op), 0)
                op_label = st.selectbox("条件", [l for l, _ in jp_ops], index=op_idx, key=f"myedit_pref_op_{i}")
                op_new = next(code for l, code in jp_ops if l == op_label)
            with c4:
                val_new = st.text_input("値", value=str(p.get("criteria", {}).get("value", "")), key=f"myedit_pref_val_{i}")
            with c5:
                if st.button("×", key=f"myedit_pref_del_{i}"):
                    prefer_list.pop(i)
                    st.session_state.myedit_prefer = prefer_list
                    st.rerun()
            prefer_list[i] = {
                "order": i + 1,
                "name": name_val,
                "criteria": {"category": cat_new, "operator": op_new, "value": val_new},
            }
            # 優先順位の上げ下げ
            if i > 0:
                if st.button("↑ 優先度を上げる", key=f"myedit_pref_up_{i}"):
                    prefer_list[i], prefer_list[i - 1] = prefer_list[i - 1], prefer_list[i]
                    for j in range(len(prefer_list)):
                        prefer_list[j]["order"] = j + 1
                    st.session_state.myedit_prefer = prefer_list
                    st.rerun()

    if len(prefer_list) < PREFER_MAX:
        if st.button("+ 優先条件を追加", key="myedit_pref_add"):
            prefer_list.append({
                "order": len(prefer_list) + 1,
                "name": "",
                "criteria": {"category": MUST_CATEGORIES_LIST[0], "operator": "le", "value": ""},
            })
            st.session_state.myedit_prefer = prefer_list
            st.rerun()

    st.markdown("---")

    # Avoid
    st.markdown("#### 回避条件 - 最大2個")
    st.caption("条件を満たす馬は下位に。避けたい馬の特徴を設定します。")
    for i, a in enumerate(avoid_list):
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 2, 0.5])
            with c1:
                name_val = st.text_input(
                    "条件名", value=a.get("name", ""),
                    key=f"myedit_avoid_name_{i}",
                    placeholder="例: 人気薄すぎ",
                )
            with c2:
                cat = a.get("criteria", {}).get("category", MUST_CATEGORIES_LIST[0])
                cat_idx = MUST_CATEGORIES_LIST.index(cat) if cat in MUST_CATEGORIES_LIST else 0
                cat_new = st.selectbox("項目", MUST_CATEGORIES_LIST, index=cat_idx, key=f"myedit_avoid_cat_{i}")
            with c3:
                op = a.get("criteria", {}).get("operator", "ge")
                jp_ops = _get_operator_labels()
                op_idx = next((k for k, (_, code) in enumerate(jp_ops) if code == op), 0)
                op_label = st.selectbox("条件", [l for l, _ in jp_ops], index=op_idx, key=f"myedit_avoid_op_{i}")
                op_new = next(code for l, code in jp_ops if l == op_label)
            with c4:
                val_new = st.text_input("値", value=str(a.get("criteria", {}).get("value", "")), key=f"myedit_avoid_val_{i}")
            with c5:
                if st.button("×", key=f"myedit_avoid_del_{i}"):
                    avoid_list.pop(i)
                    st.session_state.myedit_avoid = avoid_list
                    st.rerun()
            avoid_list[i] = {
                "name": name_val,
                "criteria": {"category": cat_new, "operator": op_new, "value": val_new},
            }

    if len(avoid_list) < AVOID_MAX:
        if st.button("+ 回避条件を追加", key="myedit_avoid_add"):
            avoid_list.append({
                "name": "",
                "criteria": {"category": MUST_CATEGORIES_LIST[0], "operator": "ge", "value": ""},
            })
            st.session_state.myedit_avoid = avoid_list
            st.rerun()

    # 保存/キャンセル
    st.markdown("---")
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("保存", type="primary", key="mylogic_save_pa", use_container_width=True):
            from logic_store import save_prefer_avoid
            from models.prefer_avoid import PreferAvoidLogic, PreferCondition, AvoidCondition
            prefer_objs = [PreferCondition.from_dict(p) for p in prefer_list if p.get("name", "").strip()]
            avoid_objs = [AvoidCondition.from_dict(a) for a in avoid_list if a.get("name", "").strip()]
            if prefer_objs or avoid_objs:
                save_prefer_avoid(selected, PreferAvoidLogic(prefer=prefer_objs, avoid=avoid_objs))
            else:
                # 全条件クリアの場合
                from logic_store import _save_field
                _save_field(selected, "prefer_avoid", None)
            _cancel_edit()
            st.success("優先/回避条件を保存しました。")
            st.rerun()
    with col_cancel:
        if st.button("キャンセル", key="mylogic_cancel_pa", use_container_width=True):
            _cancel_edit()
            st.rerun()


# ────────────────────────────────────────────
# 既存のヘルパー関数（維持）
# ────────────────────────────────────────────

def _render_performance_summary(selected: str, rec: dict, can_sim: bool):
    """バックテスト結果とフォワード成績を並列表示"""
    from logic_store import load_forward_record

    _owner = st.session_state.get("auth_user", "")
    record = load_forward_record(selected, owner=_owner)
    has_forward = record and record.results
    has_bt = "bt_result" in st.session_state and st.session_state.get("bt_result_name") == selected

    if not has_forward and not has_bt:
        return

    st.divider()
    st.subheader("成績サマリ")
    col_bt, col_fw = st.columns(2)

    with col_bt:
        st.markdown("**バックテスト**")
        if has_bt:
            r = st.session_state.bt_result
            st.metric("回収率", f"{r.get('回収率', 0)}%")
            st.metric("的中率", f"{r.get('的中率', 0)}%")
            st.metric("試行回数", f"{r.get('試行回数', 0)} 回")
        elif can_sim:
            st.caption("まだ実行されていません。「バックテスト」ページで実行できます。")
        else:
            st.caption("バックテスト不可")

    with col_fw:
        st.markdown("**フォワード成績**")
        if has_forward:
            st.metric("回収率", f"{record.recovery_rate():.1f}%")
            st.metric("的中率", f"{record.hit_rate():.1f}%")
            st.metric("試行回数", f"{record.total_trials()} 回")
        else:
            st.caption("まだ記録がありません。「コミュニティ」→「フォワード成績」で記録できます。")


def _render_custom_vars(selected: str, rec: dict):
    """カスタム変数の表示・編集"""
    from logic_store import load_custom_vars, save_custom_vars
    from models.custom_variable import (
        CustomVariable, CustomVariableSet, CustomVarType,
        CUSTOM_VAR_MAX, CUSTOM_VAR_TYPE_LIST, THREE_LEVEL_OPTIONS,
    )

    st.caption("カスタム変数を含むロジックはバックテスト不可になります（上級者向け）")

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
                if var_type == CustomVarType.BOOLEAN.value:
                    default_val = st.checkbox("デフォルト値", value=bool(v.get("default_value", False)), key=f"cv_def_{i}")
                elif var_type == CustomVarType.THREE_LEVEL.value:
                    current_default = v.get("default_value", THREE_LEVEL_OPTIONS[0])
                    tl_idx = THREE_LEVEL_OPTIONS.index(current_default) if current_default in THREE_LEVEL_OPTIONS else 0
                    default_val = st.selectbox("デフォルト値", THREE_LEVEL_OPTIONS, index=tl_idx, key=f"cv_def_{i}")
                else:
                    default_val = st.text_input("デフォルト値（数値）", value=str(v.get("default_value", "")), key=f"cv_def_{i}")
            with c4:
                if st.button("×", key=f"cv_del_{i}"):
                    cv_list.pop(i)
                    st.session_state.cv_vars = cv_list
                    st.rerun()
            cv_list[i] = {"name": var_name, "var_type": var_type, "default_value": default_val}

    col_add, col_save = st.columns(2)
    with col_add:
        if len(cv_list) < CUSTOM_VAR_MAX and st.button("+ カスタム変数を追加", key="cv_add"):
            cv_list.append({"name": "", "var_type": CUSTOM_VAR_TYPE_LIST[0], "default_value": False})
            st.session_state.cv_vars = cv_list
            st.rerun()
    with col_save:
        if st.button("カスタム変数を保存", key="cv_save") and selected:
            # バリデーション
            errors = []
            seen_names = set()
            for idx, v in enumerate(cv_list):
                vname = v.get("name", "").strip()
                if not vname:
                    errors.append(f"変数 {idx + 1}: 変数名が未入力")
                elif vname in seen_names:
                    errors.append(f"変数 {idx + 1}: 「{vname}」が重複")
                seen_names.add(vname)
                if v.get("var_type") == CustomVarType.NUMERIC.value:
                    dv = str(v.get("default_value", "")).strip()
                    if dv:
                        try:
                            float(dv)
                        except ValueError:
                            errors.append(f"変数 {idx + 1}: デフォルト値が数値ではありません")
            if errors:
                for err in errors:
                    st.warning(err)
            else:
                vars_objs = []
                for v in cv_list:
                    vt = next((t for t in CustomVarType if t.value == v["var_type"]), CustomVarType.BOOLEAN)
                    dv = v.get("default_value")
                    if vt == CustomVarType.NUMERIC and dv is not None:
                        dv_str = str(dv).strip()
                        dv = float(dv_str) if dv_str else None
                    vars_objs.append(CustomVariable(name=v["name"].strip(), var_type=vt, default_value=dv))
                save_custom_vars(selected, CustomVariableSet(variables=vars_objs))
                st.success(f"カスタム変数を保存しました。")


def _render_marketplace_listing(selected: str, rec: dict, can_sim: bool, owner: str):
    """マーケットプレイス出品ボタン・ステータス表示"""
    import marketplace_store

    logic_key = f"{owner}::{selected}"

    if marketplace_store.is_listed(logic_key):
        listing = marketplace_store.get_listing(logic_key)
        st.info(f"出品中（{listing.get('price', 0):,} pt / 購入者: {listing.get('purchase_count', 0)}人）")
        if st.button("マーケットプレイスで管理", key="mylogic_goto_mp"):
            st.session_state.nav_page = "マーケットプレイス"
            st.rerun()
        return

    if not can_sim:
        return

    # 出品フォーム
    with st.expander("マーケットプレイスに出品する"):
        desc = st.text_area(
            "説明文（ロジックの詳細は非公開です）",
            max_chars=200,
            key="mylogic_mp_desc",
        )
        price = st.number_input(
            "価格（ポイント）", min_value=1, value=100,
            key="mylogic_mp_price",
        )

        if st.button("出品する", type="primary", key="mylogic_mp_submit"):
            if not desc.strip():
                st.error("説明文を入力してください。")
            else:
                from simulation import run_backtest
                from models.simulation_spec import BetType

                with st.spinner("バックテスト実行中..."):
                    try:
                        bt_win = run_backtest(rec, BetType.WIN)
                        bt_place = run_backtest(rec, BetType.PLACE)
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

                ok = marketplace_store.list_marketplace(
                    logic_key=logic_key,
                    seller=owner,
                    price=price,
                    description_short=desc.strip(),
                    backtest_win=bt_win_summary,
                    backtest_place=bt_place_summary,
                )
                if ok:
                    st.success(f"「{selected}」を{price:,}ptで出品しました。")
                    st.rerun()
                else:
                    st.error("出品に失敗しました。")
