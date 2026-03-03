"""
ロジック作成ウィザード - Scope / Must / Prefer-Avoid を一連の流れで設定。
ステップバイステップで初心者でも迷わない設計。
"""
import streamlit as st
from pages.styles import inject_custom_css, show_help, show_wizard_steps

# 定数インポート
from constants.scope_options import (
    VENUES, DISTANCE_MIN, DISTANCE_MAX, DISTANCE_STEP,
    SURFACE_TYPES, RACE_CLASSES, AGE_CONDITIONS,
)
from models.must import MUST_CATEGORIES_LIST, MUST_OPERATORS
from models.prefer_avoid import PREFER_MAX, AVOID_MAX

# 演算子の表示ラベル
OP_DISPLAY_MAP = {"eq": "=", "le": "<=", "ge": ">=", "lt": "<", "gt": ">", "in": "含む"}

WIZARD_STEPS = [
    ("1", "対象レース条件"),
    ("2", "必須条件（絞り込み）"),
    ("3", "優先・回避条件"),
    ("4", "確認・保存"),
]

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


def _init_wizard_state():
    """ウィザードのセッション状態を初期化"""
    if "wiz_step" not in st.session_state:
        st.session_state.wiz_step = 0
    if "wiz_logic_name" not in st.session_state:
        st.session_state.wiz_logic_name = ""
    if "wiz_scope" not in st.session_state:
        st.session_state.wiz_scope = {}
    if "wiz_must_blocks" not in st.session_state:
        st.session_state.wiz_must_blocks = [[]]
    if "wiz_prefer" not in st.session_state:
        st.session_state.wiz_prefer = []
    if "wiz_avoid" not in st.session_state:
        st.session_state.wiz_avoid = []
    if "wiz_description" not in st.session_state:
        st.session_state.wiz_description = ""


def _reset_wizard_state():
    """ウィザードの全状態をリセットする。"""
    st.session_state.wiz_step = 0
    st.session_state.wiz_logic_name = ""
    st.session_state.wiz_description = ""
    st.session_state.wiz_scope = {}
    st.session_state.wiz_must_blocks = [[]]
    st.session_state.wiz_prefer = []
    st.session_state.wiz_avoid = []
    for k in ("wiz_venues", "wiz_distance_min", "wiz_distance_max", "wiz_surface",
              "wiz_race_class", "wiz_age", "wiz_name_input", "wiz_desc_input"):
        st.session_state.pop(k, None)



def _ensure_scope_widget_keys():
    """ウィジェットキーが未設定の場合、wiz_scopeからまたはデフォルト値で初期化する。"""
    scope = st.session_state.wiz_scope
    multiselect_defaults = {
        "wiz_venues": ("venues", VENUES[:1]),
        "wiz_surface": ("surface", SURFACE_TYPES[:1]),
        "wiz_race_class": ("race_class", RACE_CLASSES[:1]),
        "wiz_age": ("age_condition", AGE_CONDITIONS[:1]),
    }
    for widget_key, (scope_key, default_val) in multiselect_defaults.items():
        if widget_key not in st.session_state:
            st.session_state[widget_key] = scope.get(scope_key, default_val)
    # 距離はnumber_input（int）
    if "wiz_distance_min" not in st.session_state:
        st.session_state["wiz_distance_min"] = scope.get("distance_min", 1000)
    if "wiz_distance_max" not in st.session_state:
        st.session_state["wiz_distance_max"] = scope.get("distance_max", 1800)
    if "wiz_name_input" not in st.session_state:
        st.session_state["wiz_name_input"] = st.session_state.wiz_logic_name
    if "wiz_desc_input" not in st.session_state:
        st.session_state["wiz_desc_input"] = st.session_state.wiz_description


def _render_step_scope():
    """Step 1: 対象レース条件"""
    st.subheader("Step 1: 対象レース条件を選ぶ")
    show_help(
        "どんなレースを予想の対象にするか選びます。"
        "各カテゴリから1つ以上選んでください。<br>"
        "例：「東京競馬場」「芝」「マイル（1401-1800m）」のように、"
        "あなたが得意なレースの条件を選びましょう。"
    )

    # ウィジェットキーを初期化（default/valueの代わりにkeyで制御）
    _ensure_scope_widget_keys()

    # ロジック名（keyのみで値を制御、valueは使わない）
    logic_name = st.text_input(
        "ロジック名（わかりやすい名前をつけましょう）",
        placeholder="例: 東京芝マイル狙い",
        key="wiz_name_input",
    )
    st.session_state.wiz_logic_name = logic_name

    desc = st.text_area(
        "説明（任意）",
        placeholder="例: 東京の芝マイルで前走好走馬を狙う戦略",
        key="wiz_desc_input",
        height=68,
    )
    st.session_state.wiz_description = desc

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        venues = st.multiselect(
            "競馬場",
            VENUES,
            help="対象とする競馬場を選択",
            key="wiz_venues",
        )
        st.markdown("**距離（m）**")
        dist_col1, dist_col2 = st.columns(2)
        with dist_col1:
            distance_min = st.number_input(
                "下限",
                min_value=DISTANCE_MIN,
                max_value=DISTANCE_MAX,
                step=DISTANCE_STEP,
                key="wiz_distance_min",
                help="対象距離の下限（m）",
            )
        with dist_col2:
            distance_max = st.number_input(
                "上限",
                min_value=DISTANCE_MIN,
                max_value=DISTANCE_MAX,
                step=DISTANCE_STEP,
                key="wiz_distance_max",
                help="対象距離の上限（m）",
            )
        surface = st.multiselect(
            "芝 / ダート",
            SURFACE_TYPES,
            key="wiz_surface",
        )
    with col2:
        race_class = st.multiselect(
            "クラス",
            RACE_CLASSES,
            help="未勝利・1勝・2勝・3勝・オープン・重賞など",
            key="wiz_race_class",
        )
        age = st.multiselect(
            "年齢条件",
            AGE_CONDITIONS,
            key="wiz_age",
        )

    # 状態保存
    st.session_state.wiz_scope = {
        "venues": venues,
        "distance_min": distance_min,
        "distance_max": distance_max,
        "surface": surface,
        "race_class": race_class,
        "age_condition": age,
    }

    # ナビゲーションボタン
    st.markdown("---")
    col_back, col_spacer, col_next = st.columns([1, 2, 1])
    with col_next:
        if st.button("次へ: 除外条件 →", type="primary", use_container_width=True, key="wiz_s1_next"):
            # バリデーション
            if not st.session_state.wiz_logic_name.strip():
                st.error("ロジック名を入力してください。")
                return
            if not all([venues, surface, race_class, age]):
                st.error("各カテゴリで1つ以上選択してください。")
                return
            if distance_min > distance_max:
                st.error("距離の下限は上限以下にしてください。")
                return
            st.session_state.wiz_step = 1
            st.rerun()


def _render_step_must():
    """Step 2: 必須条件（絞り込み）"""
    st.subheader("Step 2: 必須条件で馬を絞り込む")
    show_help(
        "この条件を<b>満たさない馬は自動的に除外</b>されます。<br>"
        "<b>スキップ可能</b>: 特に条件がなければそのまま「次へ」で進んでください。<br>"
        "例: 「前走着順 ≤ 5」と設定 → 前走6着以下の馬は対象外になります。"
    )

    blocks = st.session_state.wiz_must_blocks

    for i in range(len(blocks)):
        block_conditions = blocks[i] if isinstance(blocks[i], list) else []
        with st.expander(f"条件グループ {i + 1}（グループ内はOR = いずれかを満たせばOK）", expanded=True):
            for j in range(len(block_conditions)):
                cond = block_conditions[j] if isinstance(block_conditions[j], dict) else {}
                c1, c2, c3, c4 = st.columns([2, 1, 2, 0.5])
                with c1:
                    cat = st.selectbox(
                        "項目",
                        MUST_CATEGORIES_LIST,
                        index=MUST_CATEGORIES_LIST.index(cond.get("category", MUST_CATEGORIES_LIST[0]))
                        if cond.get("category") in MUST_CATEGORIES_LIST else 0,
                        key=f"wiz_must_cat_{i}_{j}",
                        help="判定に使う項目",
                    )
                with c2:
                    op_default = cond.get("operator", "le")
                    jp_operators = _get_operator_labels()
                    op_idx = next((k for k, (_, code) in enumerate(jp_operators) if code == op_default), 0)
                    op_label = st.selectbox(
                        "条件",
                        [label for label, _ in jp_operators],
                        index=op_idx,
                        key=f"wiz_must_op_{i}_{j}",
                    )
                    op = next(code for label, code in jp_operators if label == op_label)
                with c3:
                    val = st.text_input(
                        "値",
                        value=str(cond.get("value", "")),
                        key=f"wiz_must_val_{i}_{j}",
                        placeholder="例: 5",
                    )
                with c4:
                    if st.button("×", key=f"wiz_must_del_{i}_{j}"):
                        blocks[i].pop(j)
                        st.session_state.wiz_must_blocks = blocks
                        st.rerun()
                blocks[i][j] = {"category": cat, "operator": op, "value": val}

            if st.button("+ 条件を追加", key=f"wiz_must_add_{i}"):
                blocks[i].append({"category": MUST_CATEGORIES_LIST[0], "operator": "le", "value": ""})
                st.session_state.wiz_must_blocks = blocks
                st.rerun()

        if len(blocks) > 1 and st.button("このグループを削除", key=f"wiz_must_delblk_{i}"):
            blocks.pop(i)
            st.session_state.wiz_must_blocks = blocks
            st.rerun()
            break

    st.caption("複数グループ間はAND（すべて満たす必要あり）")
    if st.button("+ 条件グループを追加"):
        blocks.append([])
        st.session_state.wiz_must_blocks = blocks
        st.rerun()

    # ナビゲーション
    st.markdown("---")
    col_back, col_spacer, col_next = st.columns([1, 2, 1])
    with col_back:
        if st.button("← 戻る", use_container_width=True, key="wiz_s2_back"):
            st.session_state.wiz_step = 0
            st.rerun()
    with col_next:
        if st.button("次へ: 優先/回避 →", type="primary", use_container_width=True, key="wiz_s2_next"):
            # 値が空の条件がある場合に警告
            has_empty = False
            for block in blocks:
                for c in (block if isinstance(block, list) else []):
                    if isinstance(c, dict) and c.get("category") and not str(c.get("value", "")).strip():
                        has_empty = True
            if has_empty:
                st.warning("値が未入力の条件があります。空の条件は保存時に無視されます。")
            st.session_state.wiz_step = 2
            st.rerun()


def _render_step_prefer_avoid():
    """Step 3: 優先・回避条件"""
    st.subheader("Step 3: 優先・回避条件を設定")
    show_help(
        "Step 2を通過した馬の中から、<b>どの馬を上位にするか</b>を決めます。<br>"
        "<b>優先条件</b>: この条件を満たす馬が上位に。1番目が最も重要です。<br>"
        "<b>回避条件</b>: この条件を満たす馬は下位に。<br>"
        "<b>スキップ可能</b>: 設定しなくてもOKです。"
    )

    prefer_list = st.session_state.wiz_prefer
    avoid_list = st.session_state.wiz_avoid

    # Prefer
    st.markdown("#### 優先条件 - 最大5個")
    st.caption("条件を満たす馬ほど上位に。1番目が最も重視されます。")
    for i, p in enumerate(prefer_list):
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 2, 0.5])
            with c1:
                name_val = st.text_input(
                    "条件名",
                    value=p.get("name", ""),
                    key=f"wiz_pref_name_{i}",
                    placeholder="例: 前走好走",
                )
            with c2:
                cat = p.get("criteria", {}).get("category", MUST_CATEGORIES_LIST[0])
                cat_idx = MUST_CATEGORIES_LIST.index(cat) if cat in MUST_CATEGORIES_LIST else 0
                cat_new = st.selectbox("項目", MUST_CATEGORIES_LIST, index=cat_idx, key=f"wiz_pref_cat_{i}")
            with c3:
                op = p.get("criteria", {}).get("operator", "le")
                jp_ops = _get_operator_labels()
                op_idx = next((k for k, (_, code) in enumerate(jp_ops) if code == op), 0)
                op_label = st.selectbox("条件", [l for l, _ in jp_ops], index=op_idx, key=f"wiz_pref_op_{i}")
                op_new = next(code for l, code in jp_ops if l == op_label)
            with c4:
                val_new = st.text_input("値", value=str(p.get("criteria", {}).get("value", "")), key=f"wiz_pref_val_{i}")
            with c5:
                if st.button("×", key=f"wiz_pref_del_{i}"):
                    prefer_list.pop(i)
                    st.session_state.wiz_prefer = prefer_list
                    st.rerun()
            prefer_list[i] = {
                "order": i + 1,
                "name": name_val,
                "criteria": {"category": cat_new, "operator": op_new, "value": val_new},
            }
            # 優先順位の上げ下げ
            if i > 0:
                if st.button(f"↑ 優先度を上げる", key=f"wiz_pref_up_{i}"):
                    prefer_list[i], prefer_list[i - 1] = prefer_list[i - 1], prefer_list[i]
                    for j in range(len(prefer_list)):
                        prefer_list[j]["order"] = j + 1
                    st.session_state.wiz_prefer = prefer_list
                    st.rerun()

    if len(prefer_list) < PREFER_MAX:
        if st.button("+ 優先条件を追加", key="wiz_pref_add"):
            prefer_list.append({
                "order": len(prefer_list) + 1,
                "name": "",
                "criteria": {"category": MUST_CATEGORIES_LIST[0], "operator": "le", "value": ""},
            })
            st.session_state.wiz_prefer = prefer_list
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
                    "条件名",
                    value=a.get("name", ""),
                    key=f"wiz_avoid_name_{i}",
                    placeholder="例: 人気薄すぎ",
                )
            with c2:
                cat = a.get("criteria", {}).get("category", MUST_CATEGORIES_LIST[0])
                cat_idx = MUST_CATEGORIES_LIST.index(cat) if cat in MUST_CATEGORIES_LIST else 0
                cat_new = st.selectbox("項目", MUST_CATEGORIES_LIST, index=cat_idx, key=f"wiz_avoid_cat_{i}")
            with c3:
                op = a.get("criteria", {}).get("operator", "ge")
                jp_ops = _get_operator_labels()
                op_idx = next((k for k, (_, code) in enumerate(jp_ops) if code == op), 0)
                op_label = st.selectbox("条件", [l for l, _ in jp_ops], index=op_idx, key=f"wiz_avoid_op_{i}")
                op_new = next(code for l, code in jp_ops if l == op_label)
            with c4:
                val_new = st.text_input("値", value=str(a.get("criteria", {}).get("value", "")), key=f"wiz_avoid_val_{i}")
            with c5:
                if st.button("×", key=f"wiz_avoid_del_{i}"):
                    avoid_list.pop(i)
                    st.session_state.wiz_avoid = avoid_list
                    st.rerun()
            avoid_list[i] = {
                "name": name_val,
                "criteria": {"category": cat_new, "operator": op_new, "value": val_new},
            }

    if len(avoid_list) < AVOID_MAX:
        if st.button("+ 回避条件を追加", key="wiz_avoid_add"):
            avoid_list.append({
                "name": "",
                "criteria": {"category": MUST_CATEGORIES_LIST[0], "operator": "ge", "value": ""},
            })
            st.session_state.wiz_avoid = avoid_list
            st.rerun()

    # ナビゲーション
    st.markdown("---")
    col_back, col_spacer, col_next = st.columns([1, 2, 1])
    with col_back:
        if st.button("← 戻る", use_container_width=True, key="wiz_s3_back"):
            st.session_state.wiz_step = 1
            st.rerun()
    with col_next:
        if st.button("次へ: 確認・保存 →", type="primary", use_container_width=True, key="wiz_s3_next"):
            st.session_state.wiz_step = 3
            st.rerun()


def _render_step_confirm():
    """Step 4: 確認・保存"""
    st.subheader("Step 4: 確認して保存")
    show_help("設定内容を確認し、問題なければ「保存」ボタンを押してください。")

    logic_name = st.session_state.wiz_logic_name
    scope = st.session_state.wiz_scope
    blocks = st.session_state.wiz_must_blocks
    prefer_list = st.session_state.wiz_prefer
    avoid_list = st.session_state.wiz_avoid

    st.markdown(f"### ロジック名: **{logic_name}**")

    # Scope サマリ
    st.markdown("#### レース条件（Scope）")
    scope_cols = st.columns(5)
    labels_keys = [
        ("競馬場", "venues"), ("芝/ダート", "surface"),
        ("クラス", "race_class"), ("年齢条件", "age_condition"),
    ]
    with scope_cols[0]:
        d_min = scope.get("distance_min", "?")
        d_max = scope.get("distance_max", "?")
        st.markdown("**距離**")
        st.write(f"{d_min}m 〜 {d_max}m")
    for col, (label, key) in zip(scope_cols[1:], labels_keys):
        with col:
            vals = scope.get(key, [])
            st.markdown(f"**{label}**")
            st.write(", ".join(vals) if vals else "（未設定）")

    # Must サマリ
    st.markdown("#### 除外条件（Must）")
    has_must = False
    for bi, block in enumerate(blocks):
        valid_conds = [c for c in (block if isinstance(block, list) else [])
                       if isinstance(c, dict) and c.get("category") and str(c.get("value", "")).strip()]
        if valid_conds:
            has_must = True
            cond_strs = []
            for c in valid_conds:
                op_label = OP_DISPLAY_MAP.get(c.get("operator", ""), c.get("operator", ""))
                cond_strs.append(f"{c['category']} {op_label} {c['value']}")
            st.markdown(f"グループ {bi + 1} (OR): " + " / ".join(cond_strs))
    if not has_must:
        st.caption("（設定なし - すべての馬が対象）")

    # Prefer/Avoid サマリ
    st.markdown("#### 優先/回避条件")
    if prefer_list:
        st.markdown("**優先（Prefer）**")
        for p in sorted(prefer_list, key=lambda x: x.get("order", 999)):
            cr = p.get("criteria", {})
            op_label = OP_DISPLAY_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
            st.write(f"  {p.get('order', '?')}. {p.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
    if avoid_list:
        st.markdown("**回避（Avoid）**")
        for a in avoid_list:
            cr = a.get("criteria", {})
            op_label = OP_DISPLAY_MAP.get(cr.get("operator", ""), cr.get("operator", ""))
            st.write(f"  - {a.get('name', '')} — {cr.get('category', '')} {op_label} {cr.get('value', '')}")
    if not prefer_list and not avoid_list:
        st.caption("（設定なし）")

    # シミュレーション可否の事前判定
    from simulation import check_simulatable
    _preview_record = {
        "name": logic_name,
        "scope": scope,
        "must": {"blocks": [{"conditions": b} for b in blocks if b]} if any(b for b in blocks) else None,
        "prefer_avoid": {
            "prefer": prefer_list,
            "avoid": avoid_list,
        } if (prefer_list or avoid_list) else None,
    }
    can_sim, reason = check_simulatable(_preview_record)
    if can_sim:
        st.success("このロジックはバックテスト可能です")
    else:
        st.warning(f"バックテスト不可（{reason}）。フォワード成績のみ記録可能です。")

    # ナビゲーション
    st.markdown("---")
    col_back, col_spacer, col_save = st.columns([1, 1, 1])
    with col_back:
        if st.button("← 戻る", use_container_width=True, key="wiz_s4_back"):
            st.session_state.wiz_step = 2
            st.rerun()
    with col_save:
        if st.button("保存する", type="primary", use_container_width=True, key="wiz_s4_save"):
            _save_logic()


def _save_logic():
    """ロジックを保存する（新規作成専用：既存名と重複する場合はエラー）"""
    try:
        from logic_store import save_scope, save_must, save_prefer_avoid, save_description, list_names
        from models.scope import RaceScope
        from models.must import MustLogic, MustBlock
        from models.prefer_avoid import PreferAvoidLogic, PreferCondition, AvoidCondition

        logic_name = st.session_state.wiz_logic_name.strip()
        owner = st.session_state.get("auth_user", "")

        # 既存ロジック名との重複チェック
        existing_names = list_names(owner=owner)
        if logic_name in existing_names:
            st.error(f"「{logic_name}」は既に存在します。別の名前を付けてください。")
            return

        scope = st.session_state.wiz_scope
        blocks = st.session_state.wiz_must_blocks
        prefer_list = st.session_state.wiz_prefer
        avoid_list = st.session_state.wiz_avoid

        # Scope 保存
        race_scope = RaceScope(
            venues=scope.get("venues", []),
            surface=scope.get("surface", []),
            race_class=scope.get("race_class", []),
            age_condition=scope.get("age_condition", []),
            distance_min=scope.get("distance_min"),
            distance_max=scope.get("distance_max"),
        )
        save_scope(logic_name, race_scope, owner=owner)

        # Must 保存
        logic_blocks = []
        for b in blocks:
            conds = [c for c in (b if isinstance(b, list) else [])
                     if isinstance(c, dict) and c.get("category") and str(c.get("value", "")).strip()]
            if conds:
                logic_blocks.append(MustBlock(conditions=conds))
        if logic_blocks:
            save_must(logic_name, MustLogic(blocks=logic_blocks))

        # 説明文保存
        desc = st.session_state.get("wiz_description", "").strip()
        if desc:
            save_description(logic_name, desc)

        # Prefer/Avoid 保存
        if prefer_list or avoid_list:
            prefer_objs = [PreferCondition.from_dict(p) for p in prefer_list if p.get("name", "").strip()]
            avoid_objs = [AvoidCondition.from_dict(a) for a in avoid_list if a.get("name", "").strip()]
            if prefer_objs or avoid_objs:
                save_prefer_avoid(logic_name, PreferAvoidLogic(prefer=prefer_objs, avoid=avoid_objs))

        st.success(f"「{logic_name}」を保存しました！")
        st.balloons()

        # 次のアクション案内
        st.info(
            "**次のステップ**: サイドバーの「バックテスト」ページで、"
            "このロジックの成績を過去データで検証できます。"
        )

        # ウィザード状態をリセット
        _reset_wizard_state()
    except Exception as e:
        st.error(f"保存に失敗しました。入力内容を確認してください。")
        import logging
        logging.getLogger(__name__).exception("ロジック保存エラー")


def render():
    inject_custom_css()

    _init_wizard_state()

    st.header("ロジック作成")

    # ウィザードステップ表示
    show_wizard_steps(WIZARD_STEPS, st.session_state.wiz_step)

    # 各ステップのレンダリング
    step = st.session_state.wiz_step
    if step == 0:
        _render_step_scope()
    elif step == 1:
        _render_step_must()
    elif step == 2:
        _render_step_prefer_avoid()
    elif step == 3:
        _render_step_confirm()
