"""
仕様書ページ。
"""
import streamlit as st
from pathlib import Path
from pages.styles import inject_custom_css


def render():
    inject_custom_css()

    st.header("仕様書")
    _spec_path = Path(__file__).resolve().parent.parent.parent / "docs" / "MVP_SPEC.md"
    if _spec_path.exists():
        st.markdown(_spec_path.read_text(encoding="utf-8"))
    else:
        st.markdown("""
- **対象範囲**: 中央競馬・過去5年・平地・未勝利戦以上
- **ロジック3階層**: Scope / Must / Prefer-Avoid
- **血統**: 5世代・事前定義指標のみ
- **導出指標**: 逃げ馬数, 先行馬数, 前走位置平均との差, レースペース
- **MVPでやらないこと**: 地方競馬, 6年超データ, 血統ツリー自由編集, 重みスコア, AI自動ロジック, 買い目最適化, CSV出力
""")
