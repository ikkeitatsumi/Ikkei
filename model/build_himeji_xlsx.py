# -*- coding: utf-8 -*-
"""
姫路市夢前町戸倉 日生学園跡地 DC用地検討 収支試算 Excel（数式入り）を生成する。
  python3 model/build_himeji_xlsx.py  →  output/姫路夢前町_日生学園跡地_収支試算.xlsx

「前提条件」「DC事業」シートの青字セルを変更すると再計算される。
「感度分析」「残余法」「保有コスト」「代替出口」は himeji_dc.py の計算結果（値）を転記。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import himeji_dc as hz

OUT = os.path.join(os.path.dirname(__file__), "..", "output", "姫路夢前町_日生学園跡地_収支試算.xlsx")

BLUE = Font(color="0000FF")
BOLD = Font(bold=True)
HDR = PatternFill("solid", fgColor="DDEBF7")
SUB = PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
YEN = '#,##0'
OKU = '#,##0.0"億"'
PCT = '0.0%'


def title(ws, text, row=1):
    ws.cell(row=row, column=1, value=text).font = Font(bold=True, size=13)


def hdr(ws, row, labels, col=1):
    for i, l in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=l)
        c.font = BOLD
        c.fill = HDR
        c.border = BOX
        c.alignment = Alignment(horizontal="center")


def widths(ws, ws_widths):
    for i, w in enumerate(ws_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build():
    (site, cc, scenarios, results, sens_rc, sens_cr, residual, hold, alts,
     rents, capexes, caps) = hz.run(verbose=False)
    wb = Workbook()

    # ------------------------------------------------------------------ 前提条件
    ws = wb.active
    ws.title = "前提条件"
    title(ws, "姫路市夢前町戸倉 日生学園跡地 33.6ha  DC用地検討 前提条件　※青字は変更可")
    widths(ws, [36, 18, 56])
    hdr(ws, 3, ["項目", "値", "備考"])
    inputs = [
        ("敷地面積（㎡）", site.land_m2, "物件概要書（登記簿）335,897.83㎡ = 101,609坪"),
        ("うち 屋外運動場（㎡）", site.ground_m2, "H6.4.26 基礎調査用資料"),
        ("うち 建物敷地その他（㎡）", site.building_site_m2, "同上"),
        ("うち 実験実習地＝山林（㎡）", site.forest_m2, "同上。林地開発許可の対象になり得る"),
        ("既存建物 延床（㎡）", site.existing_gfa_m2, "校舎・体育館・寮・食堂・職員住宅等の合計（同資料）"),
        ("募集価格（円）", site.asking_price, "16億5,000万円（坪16,238円）。税込/税抜は要確認"),
        ("固定資産税評価 土地（円）", cc.land_tax_value, "平場3,000円/㎡＋山林50円/㎡ の想定"),
        ("固定資産税評価 建物（円）", cc.building_tax_value, "築40年超"),
        ("固定資産税率", cc.property_tax_rate, "都市計画区域外のため都市計画税なし"),
        ("仲介手数料率", cc.broker_fee_rate, "＋6万円、税込"),
        ("登録免許税率（土地）", cc.reg_tax_rate_land, ""),
        ("登録免許税率（建物）", cc.reg_tax_rate_bldg, ""),
        ("不動産取得税率", cc.acq_tax_rate, "山林・雑種地は宅地1/2特例なし"),
        ("その他取得費用（円）", cc.other_acq_cost, "境界確認・測量・調査"),
        ("解体単価（円/坪）", cc.demolition_per_tsubo, "RC造 校舎・寮"),
        ("解体 追加費用（円）", cc.demolition_extra, "アスベスト・杭・浄化槽等"),
        ("金利（年）", cc.loan_rate, ""),
        ("融資手数料率", cc.loan_fee, ""),
    ]
    for i, (k, v, note) in enumerate(inputs, start=4):
        ws.cell(row=i, column=1, value=k).border = BOX
        c = ws.cell(row=i, column=2, value=v)
        c.font = BLUE
        c.border = BOX
        c.number_format = PCT if isinstance(v, float) and v < 1 else YEN
        ws.cell(row=i, column=3, value=note).border = BOX
    r = 4 + len(inputs) + 1
    ws.cell(row=r, column=1, value="平場面積（㎡）").font = BOLD
    ws.cell(row=r, column=2, value="=B5+B6").number_format = YEN
    ws.cell(row=r + 1, column=1, value="募集価格 円/㎡（全体）").font = BOLD
    ws.cell(row=r + 1, column=2, value="=B9/B4").number_format = YEN
    ws.cell(row=r + 2, column=1, value="募集価格 円/㎡（平場換算・山林ゼロ評価）").font = BOLD
    ws.cell(row=r + 2, column=2, value=f"=B9/B{r}").number_format = YEN
    ws.cell(row=r + 3, column=1, value="解体費（円）").font = BOLD
    ws.cell(row=r + 3, column=2, value="=B8/3.30579*B18+B19").number_format = YEN
    ws.cell(row=r + 4, column=1, value="固都税 年額（円）").font = BOLD
    ws.cell(row=r + 4, column=2, value="=(B10+B11)*B12").number_format = YEN
    ws.cell(row=r + 5, column=1, value="取得諸経費 合計（円）").font = BOLD
    ws.cell(row=r + 5, column=2, value="=(B9*B13+60000)*1.1+B10*B14+B11*B15+(B10+B11)*B16+B17").number_format = YEN
    ws.freeze_panes = "A4"

    # ------------------------------------------------------------------ DC事業（数式）
    ws = wb.create_sheet("DC事業")
    title(ws, "データセンター開発事業 収支（ホールセール型）　※青字は変更可。前提条件シートを参照")
    widths(ws, [34, 18, 56])
    hdr(ws, 3, ["入力", "値", "備考"])
    a = scenarios["dc50"]
    dc_inputs = [
        ("IT負荷（MW）", a.it_mw, "受電容量は PUE 倍"),
        ("PUE", a.pue, ""),
        ("capex 円/MW（建屋・設備）", a.capex_per_mw, "土地・造成・系統負担金を除く。東京はUSD15.2/W≒23億/MW（T&T 2025）"),
        ("造成・インフラ（円）", a.site_works, "整地・調整池・構内道路・上下水"),
        ("系統接続・工事費負担金（円）", a.grid_connection, "接続検討の回答で確定。数億〜数十億"),
        ("通信引込（円）", a.fiber, "冗長ダークファイバー"),
        ("設計監理率（capex比）", a.design_rate, ""),
        ("予備費率（capex比）", a.contingency_rate, ""),
        ("受電待ち期間（年）", 3.0, "接続検討〜供給開始のリードタイム"),
        ("工期（月）", a.construction_months, ""),
        ("賃料 円/kW/月", a.rent_per_kw_month, "電気代は実費転嫁。東京ホールセール2.5〜3.0万の想定に対し地方は1.5〜2.2万"),
        ("稼働率", a.occupancy, ""),
        ("運営費率（賃料比）", a.opex_rate, "保守・保険・管理"),
        ("建物・償却資産税率（capex比）", a.bldg_tax_rate_on_capex, ""),
        ("キャップレート", a.exit_cap, "東京DC 4.3〜4.5%に対し地方 +0.5〜1.0pt"),
        ("開発利益率（総事業費比）", a.developer_margin, ""),
        ("土地価格（円）", site.asking_price, "募集価格。指値検討時はここを変更"),
    ]
    for i, (k, v, note) in enumerate(dc_inputs, start=4):
        ws.cell(row=i, column=1, value=k).border = BOX
        c = ws.cell(row=i, column=2, value=v)
        c.font = BLUE
        c.border = BOX
        if isinstance(v, float) and 0 < v < 1:
            c.number_format = PCT
        elif isinstance(v, float) and v != int(v):
            c.number_format = '0.00'
        else:
            c.number_format = YEN
        ws.cell(row=i, column=3, value=note).border = BOX
    # 行番号: B4 MW, B5 PUE, B6 capex/MW, B7 site, B8 grid, B9 fiber, B10 design, B11 cont,
    #         B12 wait, B13 months, B14 rent, B15 occ, B16 opex, B17 tax, B18 cap, B19 margin, B20 price
    r0 = 4 + len(dc_inputs) + 1  # 22
    hdr(ws, r0, ["費用項目", "金額（円）", "計算"])
    P = "前提条件!"
    cost_rows = [
        ("土地代", "=B20", ""),
        ("取得諸経費", f"=(B20*{P}B13+60000)*1.1+{P}B10*{P}B14+{P}B11*{P}B15+({P}B10+{P}B11)*{P}B16+{P}B17", "仲介・登免税・取得税・その他"),
        ("既存建物解体", f"={P}B8/3.30579*{P}B18+{P}B19", ""),
        ("DC建屋・設備", "=B4*B6", "MW × capex/MW"),
        ("造成・インフラ", "=B7", ""),
        ("系統接続・工事費負担金", "=B8", ""),
        ("通信引込", "=B9", ""),
        ("設計監理", f"=B{r0+4}*B10", ""),
        ("予備費", f"=B{r0+4}*B11", ""),
        ("固都税（事業期間）", f"=({P}B10+{P}B11)*{P}B12*(B12+B13/12)", "受電待ち＋工期"),
        ("金利・融資手数料", f"=(B{r0+1}+B{r0+2}+B{r0+3})*{P}B20*(B12+B13/12)+(B{r0+4}+B{r0+5}+B{r0+6}+B{r0+7}+B{r0+8}+B{r0+9})*{P}B20*(B13/12)/2+SUM(B{r0+1}:B{r0+9})*{P}B21", "土地側は全期間、建設側は工期の1/2"),
    ]
    for i, (k, f, note) in enumerate(cost_rows, start=r0 + 1):
        ws.cell(row=i, column=1, value=k).border = BOX
        c = ws.cell(row=i, column=2, value=f)
        c.number_format = YEN
        c.border = BOX
        ws.cell(row=i, column=3, value=note).border = BOX
    rt = r0 + len(cost_rows) + 1
    ws.cell(row=rt, column=1, value="総事業費").font = BOLD
    ws.cell(row=rt, column=2, value=f"=SUM(B{r0+1}:B{rt-1})").number_format = YEN
    ws.cell(row=rt, column=2).font = BOLD

    r1 = rt + 2
    hdr(ws, r1, ["収支指標", "値", "計算"])
    out_rows = [
        ("受電容量（MW）", "=B4*B5", ""),
        ("年間賃料収入", "=B4*1000*B14*12*B15", "IT kW × 賃料 × 12 × 稼働率"),
        ("年間運営費・固都税", f"=B{r1+2}*B16+B{r0+4}*B17+({P}B10+{P}B11)*{P}B12", ""),
        ("NOI", f"=B{r1+2}-B{r1+3}", ""),
        ("NOI利回り（総事業費比）", f"=B{r1+4}/B{rt}", ""),
        ("収益価格", f"=B{r1+4}/B18", "NOI ÷ cap"),
        ("含み損益（収益価格−総事業費）", f"=B{r1+6}-B{rt}", ""),
        ("開発利益率（収益価格/総事業費−1）", f"=B{r1+6}/B{rt}-1", "目標 = 開発利益率（B19）"),
        ("損益分岐賃料（円/kW/月）", f"=((B{rt}*(1+B19)*B18)+B{r0+4}*B17+({P}B10+{P}B11)*{P}B12)/(1-B16)/(B4*1000*12*B15)", "収益価格 = 総事業費×(1+利益) となる賃料"),
        ("土地代の総事業費比", f"=B20/B{rt}", ""),
        ("総事業費/MW（円）", f"=B{rt}/B4", ""),
    ]
    for i, (k, f, note) in enumerate(out_rows, start=r1 + 1):
        ws.cell(row=i, column=1, value=k).border = BOX
        c = ws.cell(row=i, column=2, value=f)
        c.border = BOX
        c.number_format = PCT if ("率" in k or "比" in k) else YEN
        ws.cell(row=i, column=3, value=note).border = BOX
    ws.freeze_panes = "A4"

    # ------------------------------------------------------------------ 規模別比較（値）
    ws = wb.create_sheet("規模別比較")
    title(ws, "DC 規模別の収支（himeji_dc.py の計算値。賃料2.0万円/kW/月・cap5.0%・capex20億/MW）")
    widths(ws, [30] + [20] * len(results))
    hdr(ws, 3, ["項目"] + [r.name for r in results.values()])
    row = 4
    keys = list(next(iter(results.values())).lines.keys())
    for k in keys:
        ws.cell(row=row, column=1, value=k).border = BOX
        for j, r in enumerate(results.values(), start=2):
            c = ws.cell(row=row, column=j, value=r.lines[k] / hz.OKU)
            c.number_format = OKU
            c.border = BOX
        row += 1
    ws.cell(row=row, column=1, value="総事業費").font = BOLD
    for j, r in enumerate(results.values(), start=2):
        c = ws.cell(row=row, column=j, value=r.total_cost / hz.OKU)
        c.number_format = OKU
        c.font = BOLD
    row += 2
    for k in next(iter(results.values())).metrics.keys():
        ws.cell(row=row, column=1, value=k).border = BOX
        for j, r in enumerate(results.values(), start=2):
            v = r.metrics[k]
            c = ws.cell(row=row, column=j)
            if "率" in k or "利回り" in k or "比" in k:
                c.value = v
                c.number_format = PCT
            elif "円/kW" in k:
                c.value = v
                c.number_format = YEN
            elif "MW" in k and "/" not in k:
                c.value = v
                c.number_format = '0.0'
            else:
                c.value = v / hz.OKU
                c.number_format = OKU
            c.border = BOX
        row += 1

    # ------------------------------------------------------------------ 感度分析（値）
    ws = wb.create_sheet("感度分析")
    title(ws, "感度分析（50MW）")
    widths(ws, [22] + [14] * 6)
    ws.cell(row=3, column=1, value="① 開発利益率  行=賃料(円/kW/月), 列=capex(億/MW)  cap5.0%").font = BOLD
    hdr(ws, 4, ["賃料＼capex"] + [f"{c/hz.OKU:.0f}億/MW" for c in capexes])
    for i, (r_, row_) in enumerate(sens_rc, start=5):
        ws.cell(row=i, column=1, value=r_).number_format = YEN
        for j, v in enumerate(row_, start=2):
            c = ws.cell(row=i, column=j, value=v)
            c.number_format = PCT
            c.border = BOX
    base = 5 + len(sens_rc) + 2
    ws.cell(row=base, column=1, value="② 含み損益（億円）  行=キャップレート, 列=賃料(円/kW/月)  capex20億/MW").font = BOLD
    hdr(ws, base + 1, ["cap＼賃料"] + [f"{r_:,}" for r_ in rents])
    for i, (cp, row_) in enumerate(sens_cr, start=base + 2):
        ws.cell(row=i, column=1, value=cp).number_format = PCT
        for j, v in enumerate(row_, start=2):
            c = ws.cell(row=i, column=j, value=v / hz.OKU)
            c.number_format = '#,##0'
            c.border = BOX

    # ------------------------------------------------------------------ 残余法（値）
    ws = wb.create_sheet("残余法")
    title(ws, "残余法: DC事業が土地に払える理論上限（開発利益15%控除後）と DC以外の出口の価格")
    widths(ws, [48, 16, 16, 60])
    hdr(ws, 3, ["DCケース", "土地価格上限", "円/㎡", "備考"])
    row = 4
    for k, v in residual.items():
        ws.cell(row=row, column=1, value=k).border = BOX
        c = ws.cell(row=row, column=2, value=(v / hz.OKU) if v is not None else "成立せず")
        c.number_format = OKU
        c.border = BOX
        c = ws.cell(row=row, column=3, value=(v / site.land_m2) if v is not None else "－")
        c.number_format = YEN
        c.border = BOX
        ws.cell(row=row, column=4, value="電力・テナントが確保できる前提の理論値。土地代は総事業費の1〜2%").border = BOX
        row += 1
    row += 1
    hdr(ws, row, ["DC以外の出口", "土地建物の価格", "年間NOI", "備考"])
    row += 1
    for k, v in alts.items():
        ws.cell(row=row, column=1, value=k).border = BOX
        c = ws.cell(row=row, column=2, value=v["土地建物の収益価格"] / hz.OKU)
        c.number_format = OKU
        c.border = BOX
        c = ws.cell(row=row, column=3, value=v["年間NOI"] / hz.OKU)
        c.number_format = OKU
        c.border = BOX
        ws.cell(row=row, column=4, value=v["備考"]).border = BOX
        row += 1
    row += 1
    ws.cell(row=row, column=1, value="募集価格").font = BOLD
    ws.cell(row=row, column=2, value=site.asking_price / hz.OKU).number_format = OKU
    ws.cell(row=row, column=3, value=site.ask_per_m2).number_format = YEN

    # ------------------------------------------------------------------ 保有コスト（値）
    ws = wb.create_sheet("保有コスト")
    title(ws, "16.5億円で取得し、受電・許認可の一次回答を待つ場合の保有コスト（金利2%・固都税・管理費500万/年）")
    widths(ws, [10, 16, 16, 18])
    hdr(ws, 3, ["年", "年額", "累計（取得諸経費含む）", "簿価合計（土地代＋累計）"])
    for i, (y, yearly, cum, total) in enumerate(hold, start=4):
        ws.cell(row=i, column=1, value=y).border = BOX
        for j, v in enumerate((yearly, cum, total), start=2):
            c = ws.cell(row=i, column=j, value=v / hz.OKU)
            c.number_format = OKU
            c.border = BOX

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print("saved:", os.path.abspath(OUT))


if __name__ == "__main__":
    build()
