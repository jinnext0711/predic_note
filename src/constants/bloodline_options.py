"""
血統指標の事前定義値（5世代対応・編集不可の生ツリーはロジックで直接触らない）。
ロジックで使用可能な指標のみ定義。
"""

# 父系カテゴリ
SIRE_LINE_CATEGORIES = [
    "サンデーサイレンス系",
    "ミスタープロスペクター系",
    "ノーザンダンサー系",
    "その他",
]

# 母父系カテゴリ（同上）
BROODMARE_SIRE_LINE_CATEGORIES = list(SIRE_LINE_CATEGORIES)

# 距離適性血統
DISTANCE_APTITUDE_BLOOD = [
    "短距離寄り",
    "中距離寄り",
    "長距離寄り",
]

# 芝／ダート適性
SURFACE_APTITUDE_BLOOD = [
    "芝向き",
    "ダート向き",
    "両対応",
]

# インブリード簡易指標
INBREED_CROSS_3X4_OR_CLOSER = ["あり", "なし"]
INBREED_CROSS_COUNT_BANDS = ["0本", "1本", "2本以上"]
