"""
ホーム画面 - アプリの概要と使い方ガイド。
初心者が迷わず始められるように設計。
"""
import streamlit as st
from pages.styles import inject_custom_css, show_help


def render():
    inject_custom_css()

    # ── ヒーローバナー ──
    st.markdown(
        '<div class="home-hero">'
        '<div class="hero-brand">TURF INTELLIGENCE OFFICE</div>'
        '<div class="hero-tagline">競馬の知性を、あなたの武器に。</div>'
        '<div class="hero-sub">Record ・ Verify ・ Predict</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 使い方ガイド
    st.subheader("はじめての方へ")
    show_help(
        "このアプリでは、あなたの競馬予想の「ルール」を3ステップで記録し、"
        "過去のレース結果で自動検証（バックテスト）できます。<br>"
        "難しい知識は不要です。画面の案内に沿って進めるだけでOKです。"
    )

    # ── 3ステップカード ──
    st.subheader("3ステップで始める")
    st.markdown(
        '<div class="step-cards">'
        # Step 1
        '<div class="step-card">'
        '<div class="step-num-badge">1</div>'
        '<h4>レース条件を選ぶ</h4>'
        '<p>「どんなレースを対象にするか」を選びます。'
        '競馬場・距離・芝/ダートなどを選択するだけ。</p>'
        '</div>'
        # Step 2
        '<div class="step-card">'
        '<div class="step-num-badge">2</div>'
        '<h4>馬の条件を決める</h4>'
        '<p>「どんな馬を狙うか」のルールを設定します。'
        '前走着順やオッズ帯などの条件で絞り込みます。</p>'
        '</div>'
        # Step 3
        '<div class="step-card">'
        '<div class="step-num-badge">3</div>'
        '<h4>検証する</h4>'
        '<p>設定したルールを過去のレースで検証。'
        '的中率・回収率がすぐにわかります。</p>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── 機能一覧（2×2カードグリッド） ──
    st.subheader("主な機能")
    st.markdown(
        '<div class="feature-grid">'
        # ロジック作成
        '<div class="feature-card">'
        '<div class="feature-icon">📝</div>'
        '<h4>ロジック作成</h4>'
        '<ul>'
        '<li>レース条件（Scope）の設定</li>'
        '<li>除外条件（Must）の設定</li>'
        '<li>優先/回避条件（Prefer/Avoid）の設定</li>'
        '<li>カスタム変数（上級者向け）</li>'
        '</ul>'
        '</div>'
        # 検証・記録
        '<div class="feature-card">'
        '<div class="feature-icon">📊</div>'
        '<h4>検証・記録</h4>'
        '<ul>'
        '<li>バックテスト（過去データで自動検証）</li>'
        '<li>フォワード成績（実際の予想結果を記録）</li>'
        '<li>他のユーザーの公開ロジック閲覧</li>'
        '</ul>'
        '</div>'
        # 予想
        '<div class="feature-card">'
        '<div class="feature-icon">🎯</div>'
        '<h4>予想</h4>'
        '<ul>'
        '<li>レース情報を入力してロジックを自動選択</li>'
        '<li>出走馬情報を入力して推奨馬を算出</li>'
        '<li>自分のロジック + 購入済みロジックを使用</li>'
        '</ul>'
        '</div>'
        # マーケットプレイス
        '<div class="feature-card">'
        '<div class="feature-icon">🏪</div>'
        '<h4>マーケットプレイス</h4>'
        '<ul>'
        '<li>他のユーザーのアルゴリズムを購入</li>'
        '<li>バックテスト成績で比較・検討</li>'
        '<li>自分のアルゴリズムを出品して収益化</li>'
        '</ul>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── 予想・マーケットプレイスのフロー ──
    st.subheader("予想・マーケットプレイスの流れ")
    st.markdown(
        '<div class="flow-diagram">'
        '<div class="flow-row">'
        '<span class="flow-item blue">ロジック作成</span>'
        '<span class="flow-arrow">→</span>'
        '<span class="flow-item green">バックテスト検証</span>'
        '<span class="flow-arrow">→</span>'
        '<span class="flow-item gold">マーケットプレイス出品</span>'
        '</div>'
        '<div class="flow-down">↓</div>'
        '<div class="flow-row">'
        '<span class="flow-item blue">レース情報入力</span>'
        '<span class="flow-arrow">→</span>'
        '<span class="flow-item blue">ロジック自動選択</span>'
        '<span class="flow-arrow">→</span>'
        '<span class="flow-item green">予想実行</span>'
        '<span class="flow-arrow">→</span>'
        '<span class="flow-item green">推奨馬表示</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── プラン比較 ──
    st.subheader("プラン")
    st.markdown(
        '<div class="plan-cards">'
        # 無料プラン
        '<div class="plan-card">'
        '<div class="plan-name">無料プラン</div>'
        '<ul>'
        '<li>ロジック記録・編集</li>'
        '<li>フォワード成績記録</li>'
        '<li>他人の公開ロジック閲覧</li>'
        '<li>他人のロジックのバックテスト（3回まで）</li>'
        '<li>予想機能・マーケットプレイス利用可</li>'
        '<li>初回1,000ポイント付与</li>'
        '</ul>'
        '</div>'
        # 有料プラン
        '<div class="plan-card premium">'
        '<div class="plan-name">有料プラン</div>'
        '<ul>'
        '<li>無料プランの全機能</li>'
        '<li>自分のロジックのバックテスト（無制限）</li>'
        '<li>他人のロジックのバックテスト（無制限）</li>'
        '</ul>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── 対象データ ──
    st.subheader("対象データ")
    st.markdown(
        "- **対象**: 中央競馬（JRA）のみ\n"
        "- **期間**: 過去5年分\n"
        "- **レース**: 平地競走・未勝利戦以上（新馬戦除外）"
    )
