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

---

# オフィス移転（EARTH昭和町ビル 1階→2階）

| パス | 内容 |
|---|---|
| `オフィス移転_EARTH昭和町ビル/docs/契約レビュー_2階事業用賃貸借契約.md` | 2階事業用賃貸借契約書（ドラフト）のレビュー、1階契約との比較、確認・交渉事項 |
| `オフィス移転_EARTH昭和町ビル/output/*.docx, *.pdf` | 01 合意解約書（Golder・壮大・セリーヌライフ・Monde）、02 退去通知書（3社宛）、03 退去精算書（3社分）、04 利益相反承認議事録（Golder/Monde）、05 名義株確認書、06 連帯保証人交代の覚書（Golder・髙比・セリーヌライフ）、07 2階の事務所共同利用同意書（Golder・壮大・セリーヌライフ）。`00_*.pdf` は全11書類のしおり付き結合版 |
| `オフィス移転_EARTH昭和町ビル/model/build_docs.js` | 上記docx/PDFの生成スクリプト。`model/` で `npm install` 後、`output/` で `CHROMIUM="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" node ../model/build_docs.js`（PDF不要なら `NO_PDF=1`）。当事者名・金額は冒頭の定数で管理 |
| `オフィス移転_EARTH昭和町ビル/source/` | 2階契約書ドラフト（PDF） |
