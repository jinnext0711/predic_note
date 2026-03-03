"""
共通スタイル定義。
各ページで inject_custom_css() を呼び出して適用する。
"""
import streamlit as st


# デザインシステム全体のカスタムCSS
CUSTOM_CSS = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+JP:wght@400;500;600;700&display=swap');

/* ── CSS変数（カラーパレット・共通値） ── */
:root {
    --deep-navy: #0B1120;
    --navy-light: #131C31;
    --slate: #1E293B;
    --mist: #94A3B8;
    --snow: #F1F5F9;
    --white: #FFFFFF;
    --electric-blue: #3B82F6;
    --electric-blue-hover: #2563EB;
    --emerald: #10B981;
    --gold: #F59E0B;
    --crimson: #EF4444;
    --purple: #8B5CF6;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 20px;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
    --shadow-hover: 0 12px 32px rgba(0,0,0,0.15);
    --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── グローバルフォント ── */
html, body, [class*="css"] {
    font-family: "Inter", "Noto Sans JP", "Hiragino Sans", sans-serif;
    color: var(--slate);
}
h1, h2, h3, h4, h5, h6 {
    font-family: "Inter", "Noto Sans JP", sans-serif;
    font-weight: 700;
    color: var(--slate);
}

/* ── メインコンテンツ ── */
.main .block-container {
    max-width: 960px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* ── サイドバー: ダークネイビー ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--deep-navy) 0%, var(--navy-light) 100%);
}
section[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.85) !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: rgba(255,255,255,0.95) !important;
}
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] .stMarkdown .caption,
section[data-testid="stSidebar"] span[data-testid="stCaptionContainer"] {
    color: var(--mist) !important;
}
/* サイドバーのディバイダー */
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}

/* ── サイドバー: ラジオボタンをナビ風リスタイル ── */
section[data-testid="stSidebar"] .stRadio > div {
    gap: 0.15rem !important;
}
section[data-testid="stSidebar"] .stRadio > div > label {
    display: flex;
    align-items: center;
    padding: 0.55rem 0.9rem;
    border-radius: var(--radius-sm);
    border-left: 3px solid transparent;
    transition: all var(--transition);
    cursor: pointer;
    font-size: 0.92rem;
    font-weight: 500;
    color: rgba(255,255,255,0.7) !important;
    background: transparent;
}
section[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(255,255,255,0.06);
    border-left-color: var(--electric-blue);
    color: rgba(255,255,255,0.95) !important;
}
section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background: rgba(59,130,246,0.12);
    border-left-color: var(--electric-blue);
    color: #FFFFFF !important;
    font-weight: 600;
}
/* ラジオボタンの丸ドットを非表示 */
section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none;
}
/* サイドバーのラジオキャプション */
section[data-testid="stSidebar"] .stRadio > div > label span[data-testid="stCaptionContainer"] {
    font-size: 0.75rem;
    color: var(--mist) !important;
}

/* ── サイドバー: ログアウトボタン ── */
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: rgba(255,255,255,0.7) !important;
    font-size: 0.85rem;
    border-radius: var(--radius-sm);
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.12) !important;
    color: #FFFFFF !important;
    transform: none;
    box-shadow: none;
}

/* ── カード: st.container(border=True) ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: var(--radius-lg) !important;
    border-color: #E2E8F0 !important;
    box-shadow: var(--shadow-sm);
    transition: all var(--transition);
    background: var(--white);
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}

/* ── メトリクス ── */
[data-testid="stMetric"] {
    background: var(--white);
    border: 1px solid #E2E8F0;
    border-radius: var(--radius-md);
    padding: 1.2rem;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricValue"] {
    font-family: "Inter", sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: var(--slate) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--mist) !important;
}

/* ── ウィザードステップ: ピル型 + コネクティングライン ── */
.wizard-steps {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0;
    margin: 1.5rem 0 2rem 0;
}
.wizard-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 1.4rem;
    border-radius: 50px;
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--mist);
    background: var(--white);
    border: 1px solid #E2E8F0;
    transition: all var(--transition);
}
.wizard-step .step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    font-size: 0.78rem;
    font-weight: 700;
    background: #E2E8F0;
    color: var(--mist);
}
.wizard-step.active {
    background: rgba(59,130,246,0.08);
    color: var(--electric-blue);
    border-color: var(--electric-blue);
    font-weight: 600;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}
.wizard-step.active .step-num {
    background: var(--electric-blue);
    color: #FFFFFF;
}
.wizard-step.done {
    background: rgba(16,185,129,0.06);
    color: var(--emerald);
    border-color: var(--emerald);
}
.wizard-step.done .step-num {
    background: var(--emerald);
    color: #FFFFFF;
}
.wizard-connector {
    width: 32px;
    height: 2px;
    background: #E2E8F0;
    flex-shrink: 0;
}
.wizard-step.done + .wizard-connector,
.wizard-connector.done {
    background: var(--emerald);
}

/* ── ボタン: グラデーション＋ホバーリフト ── */
.stButton > button {
    border-radius: var(--radius-md);
    font-weight: 600;
    font-family: "Inter", "Noto Sans JP", sans-serif;
    transition: all var(--transition);
    border: none;
    letter-spacing: 0.01em;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--electric-blue) 0%, var(--electric-blue-hover) 100%);
    color: #FFFFFF;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3);
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(59,130,246,0.4);
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

/* ── タブ: ピル型切り替えUI ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.3rem;
    background: var(--snow);
    padding: 0.3rem;
    border-radius: var(--radius-lg);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-md);
    font-weight: 500;
    padding: 0.5rem 1.2rem;
    transition: all var(--transition);
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--white);
    box-shadow: var(--shadow-sm);
    font-weight: 600;
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}

/* ── テーブル: ヘッダー強化・行ホバー ── */
.stDataFrame {
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
}
.stDataFrame thead th {
    background: var(--slate) !important;
    color: #FFFFFF !important;
    font-weight: 600;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.stDataFrame tbody tr:hover {
    background: rgba(59,130,246,0.04) !important;
}

/* ── ヘルプボックス: グラデーション背景 ── */
.help-box {
    background: linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%);
    border-left: 4px solid var(--electric-blue);
    padding: 1.2rem 1.5rem;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    margin: 1rem 0;
    font-size: 0.9rem;
    line-height: 1.8;
    color: var(--slate);
}

/* ── エクスパンダー ── */
.streamlit-expanderHeader {
    font-size: 0.95rem;
    font-weight: 600;
    font-family: "Inter", "Noto Sans JP", sans-serif;
}

/* ── ログイン画面専用CSS ── */
.login-hero {
    text-align: center;
    padding: 3rem 1rem 1.5rem 1rem;
}
.login-hero .brand-name {
    font-family: "Inter", sans-serif;
    font-size: 2.4rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    color: var(--slate);
    margin-bottom: 0.3rem;
    line-height: 1.2;
}
.login-hero .brand-sub {
    font-family: "Inter", sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.25em;
    color: var(--mist);
    text-transform: uppercase;
    margin-bottom: 0.8rem;
}
.login-hero .tagline {
    font-family: "Noto Sans JP", sans-serif;
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--slate);
    margin-bottom: 0.3rem;
}
.login-hero .tagline-sub {
    font-family: "Inter", sans-serif;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    color: var(--mist);
    text-transform: uppercase;
}

/* ── サイドバーブランドヘッダー ── */
.sidebar-brand {
    padding: 0.5rem 0 0.8rem 0;
    text-align: center;
}
.sidebar-brand .brand-main {
    font-family: "Inter", sans-serif;
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    color: #FFFFFF !important;
    text-transform: uppercase;
}
.sidebar-brand .brand-sub {
    font-family: "Inter", sans-serif;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.15em;
    color: var(--mist) !important;
}

/* ── サイドバーユーザーカード ── */
.sidebar-user-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-md);
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
}
.sidebar-user-card .user-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: #FFFFFF !important;
    margin-bottom: 0.3rem;
}
.sidebar-user-card .plan-badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 50px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.sidebar-user-card .plan-free {
    background: rgba(148,163,184,0.2);
    color: var(--mist) !important;
}
.sidebar-user-card .plan-paid {
    background: rgba(139,92,246,0.2);
    color: #A78BFA !important;
}
.sidebar-user-card .user-points {
    font-family: "Inter", sans-serif;
    font-size: 0.85rem;
    color: var(--gold) !important;
    margin-top: 0.4rem;
    font-weight: 600;
}

/* ── ホームページ用スタイル ── */
.home-hero {
    background: linear-gradient(135deg, var(--deep-navy) 0%, #162033 50%, #1a2744 100%);
    border-radius: var(--radius-xl);
    padding: 3rem 2rem;
    text-align: center;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.home-hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.home-hero .hero-brand {
    font-family: "Inter", sans-serif;
    font-size: 2rem;
    font-weight: 900;
    letter-spacing: 0.1em;
    color: #FFFFFF;
    margin-bottom: 0.2rem;
    position: relative;
}
.home-hero .hero-tagline {
    font-family: "Noto Sans JP", sans-serif;
    font-size: 1rem;
    color: rgba(255,255,255,0.8);
    margin-bottom: 0.3rem;
    position: relative;
}
.home-hero .hero-sub {
    font-family: "Inter", sans-serif;
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    color: var(--mist);
    text-transform: uppercase;
    position: relative;
}

/* ── ステップカード（ホーム） ── */
.step-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.2rem;
    margin: 1.5rem 0 2rem 0;
}
.step-card {
    background: var(--white);
    border: 1px solid #E2E8F0;
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    text-align: center;
    transition: all var(--transition);
    position: relative;
}
.step-card:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-md);
}
.step-card .step-num-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--electric-blue) 0%, var(--electric-blue-hover) 100%);
    color: #FFFFFF;
    font-family: "Inter", sans-serif;
    font-weight: 800;
    font-size: 1rem;
    margin-bottom: 0.8rem;
}
.step-card h4 {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--slate);
    margin-bottom: 0.4rem;
}
.step-card p {
    font-size: 0.82rem;
    color: var(--mist);
    line-height: 1.6;
}

/* ── 機能カードグリッド（ホーム） ── */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.2rem;
    margin: 1.5rem 0;
}
.feature-card {
    background: var(--white);
    border: 1px solid #E2E8F0;
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    transition: all var(--transition);
}
.feature-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
    border-color: var(--electric-blue);
}
.feature-card .feature-icon {
    font-size: 1.6rem;
    margin-bottom: 0.6rem;
}
.feature-card h4 {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--slate);
    margin-bottom: 0.5rem;
}
.feature-card ul {
    list-style: none;
    padding: 0;
    margin: 0;
}
.feature-card ul li {
    font-size: 0.82rem;
    color: #64748B;
    padding: 0.2rem 0;
    padding-left: 1rem;
    position: relative;
}
.feature-card ul li::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.55rem;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--electric-blue);
}

/* ── フロー表示（ホーム） ── */
.flow-diagram {
    background: var(--white);
    border: 1px solid #E2E8F0;
    border-radius: var(--radius-lg);
    padding: 1.5rem 2rem;
    margin: 1rem 0;
}
.flow-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 0.6rem 0;
}
.flow-item {
    display: inline-flex;
    align-items: center;
    padding: 0.4rem 1rem;
    border-radius: 50px;
    font-size: 0.82rem;
    font-weight: 600;
    white-space: nowrap;
}
.flow-item.blue {
    background: rgba(59,130,246,0.1);
    color: var(--electric-blue);
    border: 1px solid rgba(59,130,246,0.2);
}
.flow-item.green {
    background: rgba(16,185,129,0.1);
    color: var(--emerald);
    border: 1px solid rgba(16,185,129,0.2);
}
.flow-item.gold {
    background: rgba(245,158,11,0.1);
    color: #D97706;
    border: 1px solid rgba(245,158,11,0.2);
}
.flow-arrow {
    color: var(--mist);
    font-size: 1rem;
}
.flow-down {
    text-align: center;
    color: var(--mist);
    font-size: 1rem;
    margin: 0.2rem 0;
}

/* ── プラン比較カード（ホーム） ── */
.plan-cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
    margin: 1.5rem 0;
}
.plan-card {
    background: var(--white);
    border: 1px solid #E2E8F0;
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    position: relative;
}
.plan-card.premium {
    border: 2px solid var(--gold);
    box-shadow: 0 0 0 3px rgba(245,158,11,0.1);
}
.plan-card .plan-name {
    font-family: "Inter", "Noto Sans JP", sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--slate);
    margin-bottom: 0.8rem;
}
.plan-card.premium .plan-name {
    color: #D97706;
}
.plan-card ul {
    list-style: none;
    padding: 0;
    margin: 0;
}
.plan-card ul li {
    font-size: 0.85rem;
    color: #64748B;
    padding: 0.35rem 0;
    padding-left: 1.3rem;
    position: relative;
}
.plan-card ul li::before {
    content: '\\2713';
    position: absolute;
    left: 0;
    color: var(--emerald);
    font-weight: 700;
    font-size: 0.8rem;
}

/* ── レスポンシブ対応 ── */
@media (max-width: 768px) {
    .step-cards { grid-template-columns: 1fr; }
    .feature-grid { grid-template-columns: 1fr; }
    .plan-cards { grid-template-columns: 1fr; }
    .login-hero .brand-name { font-size: 1.6rem; }
    .home-hero .hero-brand { font-size: 1.4rem; }
}
</style>
"""


def inject_custom_css():
    """カスタムCSSを注入する"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def show_help(text: str):
    """ヘルプボックスを表示する"""
    st.markdown(f'<div class="help-box">{text}</div>', unsafe_allow_html=True)


def show_wizard_steps(steps: list, current: int):
    """
    ウィザードのステップ表示。
    steps: [("STEP 1", "レース要件"), ("STEP 2", "除外条件"), ...]
    current: 現在のステップ（0始まり）
    """
    html_parts = []
    for i, (label, desc) in enumerate(steps):
        if i < current:
            cls = "done"
            icon = "&#10003;"
        elif i == current:
            cls = "active"
            icon = str(i + 1)
        else:
            cls = ""
            icon = str(i + 1)
        html_parts.append(
            f'<div class="wizard-step {cls}">'
            f'<span class="step-num">{icon}</span> {desc}'
            f'</div>'
        )
        if i < len(steps) - 1:
            connector_cls = "done" if i < current else ""
            html_parts.append(f'<div class="wizard-connector {connector_cls}"></div>')

    st.markdown(
        '<div class="wizard-steps">' + "".join(html_parts) + '</div>',
        unsafe_allow_html=True,
    )
