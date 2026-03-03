# predic_keiba API リファレンス

主要モジュールの公開関数・クラスのリファレンスです。

---

## logic_store — ロジック永続化

ファイル: `src/logic_store.py`

ロジック（Scope / Must / Prefer-Avoid / カスタム変数）とフォワード成績の保存・読み込み。
ロジック本体は `data/logics.json`、フォワード成績は `data/forward/{logic_name}.json` に保存される。

### ロジック操作

#### `save_scope(name, scope, base_path=None) -> Path`
ロジック名と Scope を保存する。既存の同名ロジックがある場合は Scope のみ更新し、Must/Prefer-Avoid は維持する。

- `name` (str): ロジック名
- `scope` (RaceScope): Scope オブジェクト
- 戻り値: 保存先ファイルパス

#### `save_must(name, must, base_path=None) -> Path`
指定ロジックの Must を保存する。該当ロジックが無い場合は何もしない。

- `name` (str): ロジック名（Scope を先に保存すること）
- `must` (MustLogic): Must オブジェクト

#### `save_prefer_avoid(name, prefer_avoid, base_path=None) -> Path`
指定ロジックの Prefer/Avoid を保存する。

- `name` (str): ロジック名
- `prefer_avoid` (PreferAvoidLogic): Prefer/Avoid オブジェクト

#### `save_custom_vars(name, custom_vars, base_path=None) -> Path`
指定ロジックのカスタム変数を保存する。

- `name` (str): ロジック名
- `custom_vars` (CustomVariableSet): カスタム変数セット

#### `load_scope(name, base_path=None) -> Optional[RaceScope]`
ロジック名で Scope を読み込む。無ければ None。

#### `load_must(name, base_path=None) -> Optional[MustLogic]`
ロジック名で Must を読み込む。無いか未設定なら None。

#### `load_prefer_avoid(name, base_path=None) -> Optional[PreferAvoidLogic]`
ロジック名で Prefer/Avoid を読み込む。無いか未設定なら None。

#### `load_custom_vars(name, base_path=None) -> Optional[CustomVariableSet]`
ロジック名でカスタム変数セットを読み込む。無いか未設定なら None。

#### `load_all(base_path=None) -> List[dict]`
保存済みロジック一覧を dict のリストで返す。ファイル破損時は空リスト。

#### `list_names(base_path=None) -> List[str]`
保存済みロジック名の一覧を返す。

#### `delete_logic(name, base_path=None) -> bool`
指定名のロジックを削除する。成功なら True、見つからなければ False。

### フォワード成績操作

#### `save_forward_result(logic_name, result, base_path=None) -> Path`
フォワード成績に1件追加する。

- `logic_name` (str): ロジック名
- `result` (ForwardResult): 1レースの予想結果
- 戻り値: 保存先ファイルパス

```python
from logic_store import save_forward_result
from models.forward_record import ForwardResult

result = ForwardResult(
    race_id="202501010101",
    race_date="2025-01-05",
    race_name="東京5R",
    bet_type="単勝",
    horse_name="サンプルホース",
    horse_number=3,
    bet_amount=100,
    is_hit=True,
    payout=350.0,
)
save_forward_result("東京芝マイル", result)
```

#### `load_forward_record(logic_name, base_path=None) -> Optional[ForwardRecord]`
指定ロジックのフォワード成績を読み込む。無ければ None。

```python
from logic_store import load_forward_record

record = load_forward_record("東京芝マイル")
if record:
    print(f"試行: {record.total_trials()}, 的中率: {record.hit_rate():.1f}%")
```

#### `delete_forward_result(logic_name, index, base_path=None) -> bool`
フォワード成績の指定インデックスの結果を削除する。成功なら True。

---

## simulation — シミュレーション・バックテスト

ファイル: `src/simulation.py`

シミュレーション可否判定とバックテスト実行。

### `check_simulatable(logic_record) -> Tuple[bool, str]`
ロジックレコード（logics.json の1要素 dict）からシミュレーション可否を判定する。

- `logic_record` (dict): ロジックの dict 表現
- 戻り値: `(可否: bool, 不可理由: str)`。可の場合は理由が空文字

```python
from logic_store import load_all
from simulation import check_simulatable

for rec in load_all():
    can_sim, reason = check_simulatable(rec)
    print(f"{rec['name']}: {'可能' if can_sim else f'不可（{reason}）'}")
```

### `run_backtest(logic_record, bet_type, data_years=5, base_path=None) -> Dict[str, Any]`
バックテストを実行する。シミュレーション可能ロジックのみ使用可能。

- `logic_record` (dict): ロジックの dict 表現
- `bet_type` (BetType): `BetType.WIN`（単勝）または `BetType.PLACE`（複勝）
- `data_years` (int): 対象年数（デフォルト5年）
- 戻り値: 以下のキーを持つ dict

| キー | 型 | 説明 |
|------|-----|------|
| `試行回数` | int | 賭けたレース数 |
| `回収率` | float | 回収率（%） |
| `的中率` | float | 的中率（%） |
| `年別推移` | List[dict] | 年ごとの試行回数・的中率・回収率 |
| `最大ドローダウン` | float | 最大ドローダウン（円） |
| `最大連敗数` | int | 最大連敗数 |

```python
from simulation import run_backtest
from models.simulation_spec import BetType

result = run_backtest(logic_record, BetType.WIN)
print(f"回収率: {result['回収率']}%, 的中率: {result['的中率']}%")
```

### `get_simulation_output_schema() -> List[str]`
シミュレーション出力項目名のリストを返す。

---

## data.derived_indicators — 導出指標

ファイル: `src/data/derived_indicators.py`

レース・馬データから導出指標を算出する。定義は MVP 固定。

### データクラス

#### `RaceDerivedIndicators`
レース単位の導出指標。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `race_id` | str | レースID |
| `nige_count` | int | 逃げ馬数 |
| `senko_count` | int | 先行馬数 |
| `avg_position_4c` | Optional[float] | 前走4角位置平均 |
| `pace_class` | str | ペース分類（速/普/遅） |

#### `HorseDerivedIndicators`
馬単位の導出指標。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `entry_id` | str | エントリーID |
| `diff_from_avg_position_4c` | Optional[float] | 前走位置平均との差 |

### 関数

#### `compute_all(race_id, entries) -> Tuple[RaceDerivedIndicators, List[HorseDerivedIndicators]]`
レース・馬すべての導出指標をまとめて算出する。最も使いやすい統合関数。

- `race_id` (str): レースID
- `entries` (List[HorseEntry]): 出走馬リスト

```python
from data import storage
from data.derived_indicators import compute_all

entries = storage.load_entries("202501010101")
race_ind, horse_inds = compute_all("202501010101", entries)

print(f"逃げ馬数: {race_ind.nige_count}, ペース: {race_ind.pace_class}")
for h in horse_inds:
    print(f"  {h.entry_id}: 平均との差={h.diff_from_avg_position_4c}")
```

#### `compute_race_indicators(race_id, entries) -> RaceDerivedIndicators`
レース単位の導出指標のみ算出する。

#### `compute_horse_indicators(entries, avg_position_4c) -> List[HorseDerivedIndicators]`
馬単位の導出指標のみ算出する。`avg_position_4c` は `calc_avg_position_4c()` で取得可能。

#### 個別算出関数

| 関数 | 引数 | 戻り値 | 説明 |
|------|------|--------|------|
| `count_nige(entries)` | List[HorseEntry] | int | 逃げ馬数（4角位置1〜2） |
| `count_senko(entries)` | List[HorseEntry] | int | 先行馬数（4角位置3〜4） |
| `calc_avg_position_4c(entries)` | List[HorseEntry] | Optional[float] | 前走4角位置平均 |
| `calc_diff_from_avg(entry, avg)` | HorseEntry, Optional[float] | Optional[float] | 平均との差 |
| `classify_pace(entries)` | List[HorseEntry] | str | ペース分類（速/普/遅） |

---

## models.forward_record — フォワード成績モデル

ファイル: `src/models/forward_record.py`

### `ForwardResult`
1レースの予想結果。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `race_id` | str | レースID |
| `race_date` | str | レース日（YYYY-MM-DD） |
| `race_name` | Optional[str] | レース名 |
| `bet_type` | str | 券種（単勝/複勝） |
| `horse_name` | str | 予想馬名 |
| `horse_number` | Optional[int] | 馬番 |
| `bet_amount` | int | 賭け金（円） |
| `is_hit` | bool | 的中したか |
| `payout` | float | 払戻金額 |

メソッド:
- `profit() -> float`: 損益（payout - bet_amount）
- `to_dict() -> dict` / `from_dict(d) -> ForwardResult`: シリアライズ

### `ForwardRecord`
1ロジックのフォワード成績。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `logic_name` | str | ロジック名 |
| `results` | List[ForwardResult] | 結果一覧 |

集計メソッド:
- `total_trials() -> int`: 試行回数
- `total_hits() -> int`: 的中数
- `hit_rate() -> float`: 的中率（%）
- `total_bet() -> int`: 総投資額
- `total_payout() -> float`: 総回収額
- `recovery_rate() -> float`: 回収率（%）
- `total_profit() -> float`: 総損益
- `to_dict() -> dict` / `from_dict(d) -> ForwardRecord`: シリアライズ

---

## auth_store — ユーザー認証

ファイル: `src/auth_store.py`

### `register_user(username, password, base_path=None) -> Tuple[bool, str]`
ユーザー登録。ユーザー名3文字以上、パスワード6文字以上。

### `authenticate_user(username, password, base_path=None) -> Tuple[bool, str]`
ログイン認証。戻り値は `(成功したか, メッセージ)`。
