# predic_keiba

**競馬予想プロセス記録 × シミュレーション基盤**

中央競馬（JRA）に特化した「予想思考の構造化 × 過去検証可能な意思決定基盤」。単なる予想販売ではなく、ロジックの可視化と検証SaaS。

---

## 対象範囲（MVP）

| 項目 | 内容 |
|------|------|
| 対象競馬 | 中央競馬（JRA）のみ |
| データ期間 | 過去5年分 |
| 対象レース | 平地競走のみ・未勝利戦以上・新馬戦は除外 |

---

## ロジック構造（3階層）

1. **レース要件（Scope）** — 対象レースの条件（競馬場・距離・芝/ダート・クラス・年齢条件）。必須・ブロック間AND・同一カテゴリ内のみOR可。
2. **Must** — 満たさない馬を除外。ブロック間AND・同一ブロック内OR可。使用可能データ: 前走着順、前走4角位置、斤量、枠番/馬番、最終オッズ帯、血統指標など。
3. **Prefer / Avoid** — 順位付け。Prefer 最大5個・Avoid 最大2個。レキシコグラフィック方式（加点方式はMVPでは採用しない）。

---

## 開発環境のセットアップ

### 1. リポジトリの取得

```bash
git clone https://github.com/jinnext0711/predic_keiba.git
cd predic_keiba
```

### 2. 仮想環境と依存

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. アプリの起動

```bash
streamlit run src/app.py
```

ブラウザで **http://localhost:8501** を開く。

---

## ディレクトリ構成

```
predic_keiba/
├── README.md
├── requirements.txt
├── docs/
│   ├── MVP_SPEC.md              # MVP要件定義書
│   ├── CLAUDE_CODE_AGENT_TEAMS.md  # Claude Code エージェントチームの利用
│   └── 開発環境.md
├── src/
│   ├── app.py           # Streamlit UI
│   ├── logic_record.py   # ロジック記録の統合モデル
│   ├── simulation.py     # シミュレーション仕様・インターフェース
│   ├── constants/       # 選択肢・定数（Scope, 血統, 導出指標）
│   └── models/          # Scope, Must, PreferAvoid, カスタム変数, ロジック種別
├── data/
└── venv/
```

---

## ロジック種別（二車線）

- **シミュレーション可能**: 完全選択式・内部データのみ・カスタム変数なし → 過去5年バックテスト可能。
- **シミュレーション不可**: 自由入力・外部データ・カスタム変数（最大3個）のいずれか → フォワード成績のみ記録。

---

## 有料機能（MVP）

- **無料**: ロジック記録、フォワード成績表示。
- **有料**: 自分のロジックのバックテスト、他人の公開ロジックのバックテスト（回数制限あり）。

詳細は `docs/MVP_SPEC.md` を参照してください。

---

## 今後の開発タスク

開発タスク一覧は **`docs/DEV_TASKS.md`** を参照。  
UI のリッチ化は後工程で検討する。

Claude Code で**エージェントチーム**を使って並列開発する場合は **`docs/CLAUDE_CODE_AGENT_TEAMS.md`** を参照。
