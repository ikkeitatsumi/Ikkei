# -*- coding: utf-8 -*-
"""
西麻布4丁目 土地（FACE西麻布）開発事業性 収支モデル

用途別（分譲マンション / ホテル / 賃貸レジデンス / 店舗ビル建替 / 現況保有）の
収支を同一の前提で比較し、感度分析と残余法による土地適正価格を算出する。

実行:  python3 model/feasibility.py
出力:  標準出力にサマリー表、output/ に xlsx（数式入り）と md を書き出す。

金額単位: 円。表示は億円 / 万円。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict

OKU = 100_000_000
MAN = 10_000
TSUBO = 3.30579  # ㎡ / 坪

# ---------------------------------------------------------------------------
# 1. 物件・法規制前提
# ---------------------------------------------------------------------------
@dataclass
class Site:
    name: str = "西麻布4丁目 土地（FACE西麻布）"
    address: str = "東京都港区西麻布4-3-7"
    land_m2: float = 330.99                # 登記簿
    asking_price: float = 25.0 * OKU       # 税込
    # 用途地域: 第一種住居地域(60/300) + 近隣商業地域(80/400) の跨り。
    # 近商部分の割合は用途地域図で要確認。基準ケースは一住 85% / 近商 15%。
    share_kinsho: float = 0.15
    far_ichiju: float = 3.00
    far_kinsho: float = 4.00
    bcr_ichiju: float = 0.60
    bcr_kinsho: float = 0.80
    front_road_w: float = 7.1              # 西側 公道
    # 前面道路幅員による容積制限係数（住居系 0.4 / その他 0.6）
    road_coef_ichiju: float = 0.4
    road_coef_kinsho: float = 0.6
    # 現況建物
    existing_gfa_m2: float = 878.57
    existing_rent_year: float = 95_700_000
    existing_deposit: float = 20_700_000   # 承継保証金（B1B2）
    rent_months_until_vacate: int = 3      # 取得(2026/11想定)〜退去(2027/1末)

    @property
    def land_tsubo(self) -> float:
        return self.land_m2 / TSUBO

    @property
    def far_allowed(self) -> float:
        """前面道路幅員制限を反映した加重平均容積率"""
        f1 = min(self.far_ichiju, self.front_road_w * self.road_coef_ichiju)
        f2 = min(self.far_kinsho, self.front_road_w * self.road_coef_kinsho)
        return (1 - self.share_kinsho) * f1 + self.share_kinsho * f2

    @property
    def bcr_allowed(self) -> float:
        return (1 - self.share_kinsho) * self.bcr_ichiju + self.share_kinsho * self.bcr_kinsho

    @property
    def far_floor_m2(self) -> float:
        return self.land_m2 * self.far_allowed


# ---------------------------------------------------------------------------
# 2. 共通コスト前提
# ---------------------------------------------------------------------------
@dataclass
class CommonCost:
    broker_fee_rate: float = 0.03          # 仲介手数料（税抜）
    consumption_tax: float = 0.10
    # 固定資産税評価（土地）: 公示地価水準(約300万/㎡)×0.7 を想定
    land_tax_value: float = 331 * 3_000_000 * 0.7
    reg_tax_rate: float = 0.015            # 登録免許税（土地所有権移転）
    acq_tax_rate: float = 0.03 * 0.5       # 不動産取得税（宅地 1/2 特例）
    other_acq_cost: float = 15_000_000     # 司法書士・印紙・調査・測量等
    property_tax_year: float = 13_000_000  # 固都税（土地+既存建物）年額
    demolition_per_tsubo: float = 150_000  # RC・地下1階あり（東京）
    demolition_extra: float = 20_000_000   # アスベスト調査除去・埋戻し・近隣対策
    design_rate: float = 0.05              # 設計監理（本体工事比）
    site_misc: float = 30_000_000          # 地盤調査・外構・インフラ引込・近隣対策
    contingency_rate: float = 0.03         # 予備費（本体工事比）
    loan_rate: float = 0.02                # 事業資金金利（年）
    loan_fee: float = 0.005                # 融資手数料（借入額比）

    def acquisition_costs(self, price: float) -> dict:
        broker = price * self.broker_fee_rate * (1 + self.consumption_tax)
        reg = self.land_tax_value * self.reg_tax_rate
        acq = self.land_tax_value * self.acq_tax_rate
        return {
            "仲介手数料(税込)": broker,
            "登録免許税": reg,
            "不動産取得税": acq,
            "その他取得費用": self.other_acq_cost,
        }

    def demolition(self, gfa_m2: float) -> float:
        return gfa_m2 / TSUBO * self.demolition_per_tsubo + self.demolition_extra


# ---------------------------------------------------------------------------
# 3. 用途別シナリオ
# ---------------------------------------------------------------------------
@dataclass
class Result:
    name: str
    kind: str                       # "sale" or "hold"
    lines: dict = field(default_factory=dict)   # 費用内訳
    total_cost: float = 0.0
    revenue: float = 0.0            # 売上（分譲）または 年間総収入（保有）
    noi: float = 0.0                # 保有型: 年間NOI
    profit: float = 0.0             # 分譲型: 事業利益
    metrics: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


def _base_costs(site: Site, cc: CommonCost, price: float, months: int) -> dict:
    """土地取得〜解体までの共通費用。months = 事業期間（取得〜竣工/売却）"""
    lines = {"土地代": price}
    lines.update(cc.acquisition_costs(price))
    lines["固都税（事業期間）"] = cc.property_tax_year * months / 12
    lines["既存建物解体"] = cc.demolition(site.existing_gfa_m2)
    lines["退去までの賃料収入"] = -site.existing_rent_year / 12 * site.rent_months_until_vacate
    return lines


def _finance(lines: dict, cc: CommonCost, months: int, construction_key: str) -> float:
    """金利: 土地代等は全期間、工事費は期間の半分を平均残高とみなす"""
    land_part = sum(v for k, v in lines.items() if k != construction_key and v > 0)
    cons_part = lines.get(construction_key, 0)
    interest = land_part * cc.loan_rate * months / 12 + cons_part * cc.loan_rate * months / 12 * 0.5
    fee = (land_part + cons_part) * cc.loan_fee
    return interest + fee


# ---- A. 分譲マンション ------------------------------------------------------
@dataclass
class CondoAssume:
    gfa_factor: float = 1.25          # 延床 / 容積対象（共用廊下・階段・EV・地下等の不算入分）
    sellable_factor: float = 0.85     # 専有面積 / 容積対象床面積
    price_per_tsubo: float = 15_000_000
    construction_per_tsubo: float = 2_000_000   # 本体工事（延床坪）
    sales_cost_rate: float = 0.05     # 広告宣伝・販売手数料（売上比）
    months: int = 27                  # 取得〜引渡（退去3M+解体3M+工事18M+引渡3M）


def condo(site: Site, cc: CommonCost, a: CondoAssume, price: float | None = None) -> Result:
    price = site.asking_price if price is None else price
    far = site.far_floor_m2
    gfa_tsubo = far * a.gfa_factor / TSUBO
    sell_tsubo = far * a.sellable_factor / TSUBO
    lines = _base_costs(site, cc, price, a.months)
    cons = gfa_tsubo * a.construction_per_tsubo
    lines["本体工事費"] = cons
    lines["設計監理"] = cons * cc.design_rate
    lines["外構・調査・近隣対策等"] = cc.site_misc
    lines["予備費"] = cons * cc.contingency_rate
    revenue = sell_tsubo * a.price_per_tsubo
    lines["販売経費"] = revenue * a.sales_cost_rate
    lines["金利・融資手数料"] = _finance(lines, cc, a.months, "本体工事費")
    total = sum(lines.values())
    profit = revenue - total
    r = Result("分譲マンション", "sale", lines, total, revenue=revenue, profit=profit)
    r.metrics = {
        "容積対象床面積㎡": far,
        "延床面積㎡": far * a.gfa_factor,
        "専有面積㎡": far * a.sellable_factor,
        "専有面積坪": sell_tsubo,
        "想定戸数": round(sell_tsubo / 30),  # 約100㎡/戸
        "売上高": revenue,
        "総事業費": total,
        "事業利益": profit,
        "利益率(売上比)": profit / revenue if revenue else 0,
        "利益率(総事業費比)": profit / total if total else 0,
        "損益分岐坪単価(万円)": (total / sell_tsubo / MAN) if sell_tsubo else 0,
    }
    return r


# ---- B. ホテル ----------------------------------------------------------------
@dataclass
class HotelAssume:
    label: str = "アップスケール"
    gfa_factor: float = 1.06          # ホテルは廊下も容積算入。機械室等のみ不算入
    gfa_per_key_m2: float = 36.0      # 延床 / 客室（共用部込み）
    adr: float = 45_000
    occupancy: float = 0.80
    other_rev_rate: float = 0.08      # 料飲・その他（客室売上比）
    owner_noi_rate: float = 0.26      # 所有者NOI（総売上比）: 賃貸借型の賃料 or MC型の GOP−手数料−FF&E積立
    construction_per_tsubo: float = 2_200_000
    ffe_per_key: float = 4_000_000
    preopening: float = 30_000_000
    months: int = 27
    exit_cap: float = 0.045           # 港区ホテル 取引利回り想定（CBRE 2026/3 東京 4.2%に保守性上乗せ）


def hotel(site: Site, cc: CommonCost, a: HotelAssume, price: float | None = None) -> Result:
    price = site.asking_price if price is None else price
    far = site.far_floor_m2
    gfa_m2 = far * a.gfa_factor
    keys = int(gfa_m2 / a.gfa_per_key_m2)
    lines = _base_costs(site, cc, price, a.months)
    cons = gfa_m2 / TSUBO * a.construction_per_tsubo
    lines["本体工事費"] = cons
    lines["設計監理"] = cons * cc.design_rate
    lines["FF&E"] = keys * a.ffe_per_key
    lines["外構・調査・近隣対策等"] = cc.site_misc
    lines["開業準備費"] = a.preopening
    lines["予備費"] = cons * cc.contingency_rate
    lines["金利・融資手数料"] = _finance(lines, cc, a.months, "本体工事費")
    total = sum(lines.values())
    room_rev = keys * a.adr * a.occupancy * 365
    revenue = room_rev * (1 + a.other_rev_rate)
    noi = revenue * a.owner_noi_rate - cc.property_tax_year * 1.6   # 新築後は建物分の固都税増
    value = noi / a.exit_cap
    r = Result(f"ホテル（{a.label}）", "hold", lines, total, revenue=revenue, noi=noi)
    r.metrics = {
        "延床面積㎡": gfa_m2,
        "客室数": keys,
        "ADR": a.adr,
        "稼働率": a.occupancy,
        "RevPAR": a.adr * a.occupancy,
        "年間総売上": revenue,
        "所有者NOI": noi,
        "総事業費": total,
        "NOI利回り(総事業費比)": noi / total,
        "収益価格(Cap %.1f%%)" % (a.exit_cap * 100): value,
        "含み損益": value - total,
        "損益分岐ADR": _breakeven_adr(a, keys, total, cc),
    }
    return r


def _breakeven_adr(a: HotelAssume, keys: int, total: float, cc: CommonCost) -> float:
    """収益価格＝総事業費 となる ADR"""
    target_noi = total * a.exit_cap
    rev_needed = (target_noi + cc.property_tax_year * 1.6) / a.owner_noi_rate
    room_rev = rev_needed / (1 + a.other_rev_rate)
    return room_rev / (keys * a.occupancy * 365)


# ---- C. 賃貸レジデンス ----------------------------------------------------------
@dataclass
class RentalAssume:
    gfa_factor: float = 1.25
    rentable_factor: float = 0.85
    rent_per_tsubo_month: float = 22_000
    occupancy: float = 0.95
    opex_rate: float = 0.20           # 管理・修繕・PM・保険等（総収入比、固都税別）
    construction_per_tsubo: float = 2_000_000
    months: int = 27
    exit_cap: float = 0.037           # JREI 2026/4 城南ファミリー 3.7%


def rental(site: Site, cc: CommonCost, a: RentalAssume, price: float | None = None) -> Result:
    price = site.asking_price if price is None else price
    far = site.far_floor_m2
    gfa_tsubo = far * a.gfa_factor / TSUBO
    rent_tsubo = far * a.rentable_factor / TSUBO
    lines = _base_costs(site, cc, price, a.months)
    cons = gfa_tsubo * a.construction_per_tsubo
    lines["本体工事費"] = cons
    lines["設計監理"] = cons * cc.design_rate
    lines["外構・調査・近隣対策等"] = cc.site_misc
    lines["予備費"] = cons * cc.contingency_rate
    lines["金利・融資手数料"] = _finance(lines, cc, a.months, "本体工事費")
    total = sum(lines.values())
    revenue = rent_tsubo * a.rent_per_tsubo_month * 12 * a.occupancy
    noi = revenue * (1 - a.opex_rate) - cc.property_tax_year * 1.6
    value = noi / a.exit_cap
    r = Result("賃貸レジデンス", "hold", lines, total, revenue=revenue, noi=noi)
    r.metrics = {
        "延床面積㎡": far * a.gfa_factor,
        "貸室面積坪": rent_tsubo,
        "賃料坪単価/月": a.rent_per_tsubo_month,
        "年間総収入": revenue,
        "NOI": noi,
        "総事業費": total,
        "NOI利回り(総事業費比)": noi / total,
        "収益価格(Cap %.1f%%)" % (a.exit_cap * 100): value,
        "含み損益": value - total,
    }
    return r


# ---- D. 店舗ビル建替 -------------------------------------------------------------
@dataclass
class RetailAssume:
    gfa_factor: float = 1.05          # 地下も算入。機械室のみ不算入
    rentable_factor: float = 0.85
    rent_per_tsubo_month: float = 36_000   # 現行テナント 32,900〜38,600円/坪 を参考
    occupancy: float = 0.92
    opex_rate: float = 0.15
    construction_per_tsubo: float = 2_000_000
    months: int = 27
    exit_cap: float = 0.040


def retail(site: Site, cc: CommonCost, a: RetailAssume, price: float | None = None) -> Result:
    price = site.asking_price if price is None else price
    far = site.far_floor_m2
    gfa_tsubo = far * a.gfa_factor / TSUBO
    rent_tsubo = far * a.rentable_factor / TSUBO
    lines = _base_costs(site, cc, price, a.months)
    cons = gfa_tsubo * a.construction_per_tsubo
    lines["本体工事費"] = cons
    lines["設計監理"] = cons * cc.design_rate
    lines["外構・調査・近隣対策等"] = cc.site_misc
    lines["予備費"] = cons * cc.contingency_rate
    lines["金利・融資手数料"] = _finance(lines, cc, a.months, "本体工事費")
    total = sum(lines.values())
    revenue = rent_tsubo * a.rent_per_tsubo_month * 12 * a.occupancy
    noi = revenue * (1 - a.opex_rate) - cc.property_tax_year * 1.6
    value = noi / a.exit_cap
    r = Result("店舗ビル建替", "hold", lines, total, revenue=revenue, noi=noi)
    r.metrics = {
        "延床面積㎡": far * a.gfa_factor,
        "貸室面積坪": rent_tsubo,
        "賃料坪単価/月": a.rent_per_tsubo_month,
        "年間総収入": revenue,
        "NOI": noi,
        "総事業費": total,
        "NOI利回り(総事業費比)": noi / total,
        "収益価格(Cap %.1f%%)" % (a.exit_cap * 100): value,
        "含み損益": value - total,
    }
    return r


# ---- E. 現況保有（建替えず再テナント付け） ------------------------------------------
@dataclass
class HoldAssume:
    leasable_tsubo: float = 108.2 + 115.34    # レントロール
    relet_rent_per_tsubo: float = 33_000      # 再募集想定
    downtime_months: int = 6
    opex_rate: float = 0.05                   # 管理・保険（固都税別）
    capex_reserve_year: float = 8_000_000     # 築24年RC 修繕積立
    exit_cap: float = 0.035               # 港区 小規模店舗ビル NOI利回り想定


def hold(site: Site, cc: CommonCost, a: HoldAssume, price: float | None = None) -> Result:
    price = site.asking_price if price is None else price
    lines = {"土地建物代": price}
    lines.update(cc.acquisition_costs(price))
    total = sum(lines.values())
    current_gross = site.existing_rent_year
    current_noi = current_gross * (1 - a.opex_rate) - cc.property_tax_year - a.capex_reserve_year
    relet_gross = a.leasable_tsubo * a.relet_rent_per_tsubo * 12
    relet_noi = relet_gross * (1 - a.opex_rate) - cc.property_tax_year - a.capex_reserve_year
    value = relet_noi / a.exit_cap
    r = Result("現況保有（再テナント）", "hold", lines, total, revenue=relet_gross, noi=relet_noi)
    r.metrics = {
        "現行年間賃料": current_gross,
        "表面利回り(募集価格比)": current_gross / price,
        "現行NOI": current_noi,
        "現行NOI利回り(総取得費比)": current_noi / total,
        "再募集後年間賃料": relet_gross,
        "再募集後NOI": relet_noi,
        "再募集後NOI利回り": relet_noi / total,
        "空室期間逸失賃料": relet_gross / 12 * a.downtime_months,
        "収益価格(Cap %.1f%%)" % (a.exit_cap * 100): value,
        "含み損益": value - total,
    }
    return r


# ---------------------------------------------------------------------------
# 4. 残余法（土地適正価格）
# ---------------------------------------------------------------------------
def residual_land_condo(site, cc, a: CondoAssume, target_margin: float = 0.15) -> float:
    """分譲: 売上比 target_margin の利益を確保できる土地価格を二分探索"""
    lo, hi = 1 * OKU, 40 * OKU
    for _ in range(60):
        mid = (lo + hi) / 2
        m = condo(site, cc, a, price=mid).metrics["利益率(売上比)"]
        if m > target_margin:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def residual_land_hold(fn, site, cc, a, key="含み損益") -> float:
    """保有型: 収益価格 = 総事業費 となる土地価格"""
    lo, hi = 0.0, 40 * OKU
    for _ in range(60):
        mid = (lo + hi) / 2
        v = fn(site, cc, a, price=mid).metrics[key]
        if v > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------------------
# 5. 実行
# ---------------------------------------------------------------------------
def oku(v: float) -> str:
    return f"{v / OKU:,.2f}億"


def run(verbose: bool = True):
    site = Site()
    cc = CommonCost()
    ca = CondoAssume()
    results = {
        "condo": condo(site, cc, ca),
        "hotel_budget": hotel(site, cc, HotelAssume(label="宿泊特化", gfa_per_key_m2=28, adr=28_000, occupancy=0.85, other_rev_rate=0.03, ffe_per_key=2_500_000, construction_per_tsubo=2_000_000)),
        "hotel_upscale": hotel(site, cc, HotelAssume()),
        "hotel_luxury": hotel(site, cc, HotelAssume(label="ラグジュアリー", gfa_per_key_m2=50, adr=90_000, occupancy=0.72, other_rev_rate=0.15, ffe_per_key=8_000_000, construction_per_tsubo=2_600_000, exit_cap=0.045)),
        "rental": rental(site, cc, RentalAssume()),
        "retail": retail(site, cc, RetailAssume()),
        "hold": hold(site, cc, HoldAssume()),
    }

    # 感度: 分譲 坪単価 × 土地価格
    prices = [18e8, 20e8, 22e8, 25e8]
    unit_prices = [12e6, 14e6, 15e6, 16e6, 18e6, 20e6]
    sens = []
    for up in unit_prices:
        row = []
        for p in prices:
            m = condo(site, cc, CondoAssume(price_per_tsubo=up), price=p).metrics
            row.append((m["事業利益"], m["利益率(売上比)"]))
        sens.append((up, row))

    # 感度: 容積率（近商割合）
    far_cases = []
    for label, share in [("保守（全て一住・道路幅員284%）", 0.0), ("基準（近商15%）", 0.15), ("上振れ（近商40%）", 0.40)]:
        s2 = Site(share_kinsho=share)
        m = condo(s2, cc, ca).metrics
        far_cases.append((label, s2.far_allowed, m["専有面積坪"], m["事業利益"], m["利益率(売上比)"]))

    # 残余法
    residual = {
        "分譲(坪1,500万・利益率15%)": residual_land_condo(site, cc, ca, 0.15),
        "分譲(坪1,800万・利益率15%)": residual_land_condo(site, cc, CondoAssume(price_per_tsubo=18e6), 0.15),
        "ホテル(アップスケール・収益価格=事業費)": residual_land_hold(hotel, site, cc, HotelAssume()),
        "ホテル(ラグジュアリー・収益価格=事業費)": residual_land_hold(hotel, site, cc, HotelAssume(label="ラグジュアリー", gfa_per_key_m2=50, adr=90_000, occupancy=0.72, other_rev_rate=0.15, ffe_per_key=8_000_000, construction_per_tsubo=2_600_000)),
        "賃貸レジデンス(収益価格=事業費)": residual_land_hold(rental, site, cc, RentalAssume()),
        "店舗ビル建替(収益価格=事業費)": residual_land_hold(retail, site, cc, RetailAssume()),
        "現況保有(収益価格=取得費)": residual_land_hold(hold, site, cc, HoldAssume()),
    }

    if verbose:
        print(f"敷地 {site.land_m2}㎡ ({site.land_tsubo:.2f}坪)  募集価格 {oku(site.asking_price)}  坪単価 {site.asking_price / site.land_tsubo / MAN:,.0f}万円/坪")
        print(f"許容容積率 {site.far_allowed * 100:.0f}%  容積対象床面積 {site.far_floor_m2:.0f}㎡  許容建ぺい率 {site.bcr_allowed * 100:.0f}%")
        print()
        for k, r in results.items():
            print(f"=== {r.name} ===")
            for kk, v in r.lines.items():
                print(f"  {kk:<16}{oku(v):>12}")
            print(f"  {'総事業費':<16}{oku(r.total_cost):>12}")
            for kk, v in r.metrics.items():
                if isinstance(v, float) and abs(v) >= 1e6:
                    print(f"  {kk:<24}{oku(v):>12}")
                elif isinstance(v, float) and v < 1:
                    print(f"  {kk:<24}{v * 100:>11.1f}%")
                else:
                    print(f"  {kk:<24}{v:>12,.0f}")
            print()
        print("=== 感度分析: 分譲 事業利益（億円）/ 利益率  行=販売坪単価, 列=土地価格 ===")
        print("坪単価\\土地  " + "".join(f"{p / OKU:>14.0f}億" for p in prices))
        for up, row in sens:
            print(f"{up / MAN:>7,.0f}万   " + "".join(f"{v / OKU:>8.1f}({m * 100:>4.0f}%)" for v, m in row))
        print()
        print("=== 感度分析: 容積率ケース（分譲・坪1,500万・土地25億） ===")
        for label, far, tsubo, pr, mg in far_cases:
            print(f"  {label:<24} 容積 {far * 100:.0f}%  専有 {tsubo:.0f}坪  利益 {oku(pr)} ({mg * 100:.1f}%)")
        print()
        print("=== 残余法による土地価格（用途別に支払可能な上限） ===")
        for k, v in residual.items():
            print(f"  {k:<28}{oku(v):>10}  ({v / site.land_tsubo / MAN:,.0f}万円/坪)")
    return site, cc, results, sens, far_cases, residual, prices, unit_prices


if __name__ == "__main__":
    run()
