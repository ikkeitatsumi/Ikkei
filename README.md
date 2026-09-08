# 西麻布4丁目 土地（FACE西麻布）開発事業性検討

港区西麻布4-3-7 の土地（330.99㎡・募集価格25億円）について、ホテル / 分譲マンション / 賃貸レジデンス / 店舗ビル建替 / 現況保有 の収支を同一前提で比較し、残余法で支払可能な土地価格を算出したプロジェクト。

## 構成

| パス | 内容 |
|---|---|
| `docs/西麻布4丁目_開発事業性検討レポート.md` | 結論・法規制・用途別収支・感度分析・残余法・交渉方針・DD項目・出典 |
| `output/西麻布4丁目_収支試算.xlsx` | 数式入り試算表。「前提条件」「分譲マンション」「ホテル」シートの青字セルを変更すると再計算 |
| `model/feasibility.py` | 収支モデル本体（Python）。`python3 model/feasibility.py` で全シナリオを標準出力 |
| `model/build_xlsx.py` | モデルから xlsx を生成。`python3 model/build_xlsx.py` |
| `source/FACE西麻布_物件概要書.pdf` | 仲介業者提供の概要書・地図・レントロール |

## 使い方

```bash
pip install openpyxl
python3 model/feasibility.py     # シナリオ比較・感度分析・残余法を表示
python3 model/build_xlsx.py      # output/ に xlsx を再生成
```

前提を変えたい場合は `model/feasibility.py` の `Site` / `CommonCost` / 各 `*Assume` データクラスの既定値を編集する。
