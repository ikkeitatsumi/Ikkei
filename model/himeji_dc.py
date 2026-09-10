# -*- coding: utf-8 -*-
"""
姫路市夢前町戸倉 日生学園（旧 自由ヶ丘高等学校）跡地 33.6ha
データセンター（DC）用地としての事業性 収支モデル

土山町山中 DC適地調査（2026-08-19, Golder）の評価フレームを踏襲し、
  (1) DC事業者から見た本敷地の事業収支と、土地に払える理論上限（残余法）
  (2) 取得後、受電確認を待つ期間の保有コスト
  (3) DC以外の出口（現況一括賃貸 / 太陽光 / 系統用蓄電池 / 産業用地分譲 / 山林保有）
      から見た土地価格
を同一前提で並べる。

実行:  python3 model/himeji_dc.py
金額単位: 円（表示は億円）。面積: ㎡。電力: kW（IT負荷）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

OKU = 100_000_000
MAN = 10_000
TSUBO = 3.30579  # ㎡ / 坪


# ---------------------------------------------------------------------------
# 1. 物件前提（物件概要書 + 基礎調査用資料 H6.4.26）
# ---------------------------------------------------------------------------
@dataclass
class Site:
    name: str = "姫路市夢前町戸倉 日生学園（旧 自由ヶ丘高等学校）跡地"
    address: str = "兵庫県姫路市夢前町戸倉566番"
    land_m2: float = 335_897.83            # 概要書（登記簿）
    asking_price: float = 16.5 * OKU       # 概要書。税込/税抜の別は未記載
    # 土地の内訳（H6.4.26 基礎調査用資料。合計は登記面積と0.4%差）
    ground_m2: float = 41_971.0            # 屋外運動場（野球場・陸上競技場・テニス・ゴルフ練習場等）
    building_site_m2: float = 68_600.0     # 建物敷地 その他
    forest_m2: float = 226_694.0           # 実験実習地（山林）
    # 既存建物（同資料。延床合計 約27,500㎡）
    existing_gfa_m2: float = 27_523.0
    built_year: int = 1983                 # 日生学園第三高校 開校年。増築分は不明
    closed_year: int = 2021                # 休校（2021年4月1日）
    # 都市計画: 都市計画区域外（姫路市: 旧夢前町全域）。用途地域・建ぺい・容積の指定なし
    city_planning_area: bool = False

    @property
    def land_tsubo(self) -> float:
        return self.land_m2 / TSUBO

    @property
    def flat_m2(self) -> float:
        """平場（運動場＋建物敷地）。DC建屋・受変電・発電機ヤードの器になる面積"""
        return self.ground_m2 + self.building_site_m2

    @property
    def ask_per_m2(self) -> float:
        return self.asking_price / self.land_m2

    @property
    def ask_per_flat_m2(self) -> float:
        """山林をゼロ評価した場合の平場単価"""
        return self.asking_price / self.flat_m2


# ---------------------------------------------------------------------------
# 2. 共通コスト（取得・解体・保有）
# ---------------------------------------------------------------------------
@dataclass
class CommonCost:
    broker_fee_rate: float = 0.03
    consumption_tax: float = 0.10
    # 固定資産税評価（想定）: 平場 11.06ha × 3,000円/㎡ ≒ 3.3億 ＋ 山林 22.7ha × 50円/㎡ ≒ 0.1億
    land_tax_value: float = 3.4 * OKU
    building_tax_value: float = 1.0 * OKU  # 築40年超の校舎・寮。残価は小さい想定
    reg_tax_rate_land: float = 0.015       # 登録免許税（土地 所有権移転）
    reg_tax_rate_bldg: float = 0.020       # 同（建物）
    acq_tax_rate: float = 0.03             # 不動産取得税（山林・雑種地は宅地1/2特例なし）
    other_acq_cost: float = 0.4 * OKU      # 境界確認・地積測量（33haの確定測量は非現実的）・調査・司法書士
    property_tax_rate: float = 0.014       # 固定資産税。都市計画区域外のため都市計画税なし
    demolition_per_tsubo: float = 70_000   # RC造 校舎・寮（地方・大規模）
    demolition_extra: float = 1.5 * OKU    # アスベスト（1983年築）・杭・浄化槽・受水槽・残置物
    loan_rate: float = 0.02
    loan_fee: float = 0.005

    def acquisition_costs(self, price: float) -> dict:
        broker = (price * self.broker_fee_rate + 60_000) * (1 + self.consumption_tax)
        return {
            "仲介手数料(税込)": broker,
            "登録免許税": self.land_tax_value * self.reg_tax_rate_land + self.building_tax_value * self.reg_tax_rate_bldg,
            "不動産取得税": (self.land_tax_value + self.building_tax_value) * self.acq_tax_rate,
            "その他取得費用": self.other_acq_cost,
        }

    def property_tax_year(self) -> float:
        return (self.land_tax_value + self.building_tax_value) * self.property_tax_rate

    def demolition(self, gfa_m2: float) -> float:
        return gfa_m2 / TSUBO * self.demolition_per_tsubo + self.demolition_extra


# ---------------------------------------------------------------------------
# 3. データセンター事業（ホールセール型・自社開発して運用事業者に賃貸）
# ---------------------------------------------------------------------------
@dataclass
class DCAssume:
    label: str = "郊外型 50MW"
    it_mw: float = 50.0                    # IT負荷（受電はPUE1.3で約65MW）
    pue: float = 1.3
    capex_per_mw: float = 20.0 * OKU       # 建屋＋電気・空調設備（土地・造成・系統負担金を除く）
    site_works: float = 5.0 * OKU          # 整地・調整池・構内道路・上下水
    grid_connection: float = 20.0 * OKU    # 特高引込・工事費負担金（距離・増強要否で数億〜数十億）
    fiber: float = 3.0 * OKU               # 冗長ダークファイバー引込
    design_rate: float = 0.04              # 設計監理（capex比）
    contingency_rate: float = 0.05         # 予備費（capex比）
    construction_months: int = 30          # 着工〜竣工
    rent_per_kw_month: float = 20_000      # ホールセール賃料（電気代は実費転嫁）
    occupancy: float = 0.90                # 安定稼働時
    opex_rate: float = 0.20                # 運営費（賃料比。保守・保険・管理。電気代除く）
    bldg_tax_rate_on_capex: float = 0.006  # 固定資産税・償却資産税（capex比、平均的な評価で概算）
    exit_cap: float = 0.050                # 地方DCのキャップレート（東京 4.3〜4.5%に対し+0.5〜1.0pt）
    developer_margin: float = 0.15         # 開発利益（総事業費比）

    @property
    def it_kw(self) -> float:
        return self.it_mw * 1_000

    @property
    def receiving_mw(self) -> float:
        return self.it_mw * self.pue


@dataclass
class Result:
    name: str
    lines: dict = field(default_factory=dict)
    total_cost: float = 0.0
    revenue: float = 0.0
    noi: float = 0.0
    metrics: dict = field(default_factory=dict)


def dc(site: Site, cc: CommonCost, a: DCAssume, price: float | None = None,
       wait_years: float = 3.0) -> Result:
    """DC開発事業の収支。wait_years は取得から着工までの受電待ち期間。"""
    price = site.asking_price if price is None else price
    lines = {"土地代": price}
    lines.update(cc.acquisition_costs(price))
    lines["既存建物解体"] = cc.demolition(site.existing_gfa_m2)
    capex = a.it_mw * a.capex_per_mw
    lines["DC建屋・設備"] = capex
    lines["造成・インフラ"] = a.site_works
    lines["系統接続・工事費負担金"] = a.grid_connection
    lines["通信引込"] = a.fiber
    lines["設計監理"] = capex * a.design_rate
    lines["予備費"] = capex * a.contingency_rate
    years = wait_years + a.construction_months / 12
    lines["固都税(事業期間)"] = cc.property_tax_year() * years
    # 金利: 土地は全期間、建設費は工期の半分
    land_side = price + sum(cc.acquisition_costs(price).values()) + lines["既存建物解体"]
    build_side = capex + a.site_works + a.grid_connection + a.fiber + lines["設計監理"] + lines["予備費"]
    interest = land_side * cc.loan_rate * years + build_side * cc.loan_rate * (a.construction_months / 12) / 2
    lines["金利・融資手数料"] = interest + (land_side + build_side) * cc.loan_fee
    total = sum(lines.values())

    gross = a.it_kw * a.rent_per_kw_month * 12 * a.occupancy
    opex = gross * a.opex_rate + capex * a.bldg_tax_rate_on_capex + cc.property_tax_year()
    noi = gross - opex
    value = noi / a.exit_cap
    metrics = {
        "受電容量MW": a.receiving_mw,
        "年間賃料収入": gross,
        "年間運営費・固都税": opex,
        "NOI": noi,
        "NOI利回り(総事業費比)": noi / total,
        "収益価格": value,
        "含み損益(収益価格-総事業費)": value - total,
        "開発利益率(収益価格/総事業費-1)": value / total - 1,
        "損益分岐賃料(円/kW/月)": _breakeven_rent(a, cc, capex, total),
        "土地代の総事業費比": price / total,
        "総事業費/MW": total / a.it_mw,
    }
    return Result(a.label, lines, total, gross, noi, metrics)


def _breakeven_rent(a: DCAssume, cc: CommonCost, capex: float, total: float) -> float:
    """収益価格 = 総事業費 × (1+開発利益) となる賃料"""
    target_noi = total * (1 + a.developer_margin) * a.exit_cap
    fixed = capex * a.bldg_tax_rate_on_capex + cc.property_tax_year()
    gross = (target_noi + fixed) / (1 - a.opex_rate)
    return gross / (a.it_kw * 12 * a.occupancy)


def residual_land_dc(site: Site, cc: CommonCost, a: DCAssume, wait_years: float = 3.0) -> float:
    """収益価格 = 総事業費 × (1+開発利益) を満たす土地価格（二分法）"""
    lo, hi = -50 * OKU, 3_000 * OKU
    for _ in range(80):
        mid = (lo + hi) / 2
        r = dc(site, cc, a, price=max(mid, 0.0), wait_years=wait_years)
        if r.metrics["収益価格"] >= r.total_cost * (1 + a.developer_margin):
            lo = mid
        else:
            hi = mid
    if lo <= 0:
        return None  # 土地代ゼロでも目標利益に届かない＝成立せず
    return lo


# ---------------------------------------------------------------------------
# 4. 取得後の保有コスト（受電・許認可の一次回答を待つ期間）
# ---------------------------------------------------------------------------
def holding_cost(site: Site, cc: CommonCost, price: float | None = None, years: int = 5,
                 mgmt_year: float = 0.05 * OKU) -> list:
    """年次の累積保有コスト。mgmt_year: 草刈・巡回・警備・建物最低限維持"""
    price = site.asking_price if price is None else price
    acq = sum(cc.acquisition_costs(price).values())
    rows = []
    cum = acq
    for y in range(1, years + 1):
        yearly = price * cc.loan_rate + cc.property_tax_year() + mgmt_year
        cum += yearly
        rows.append((y, yearly, cum, price + cum))
    return rows


# ---------------------------------------------------------------------------
# 5. DC以外の出口
# ---------------------------------------------------------------------------
@dataclass
class AltAssume:
    # 現況一括賃貸（研修所・合宿所・通信制高校スクーリング拠点・技能実習研修寮 等）
    asis_rent_year: float = 0.40 * OKU     # 寮90室・食堂・体育館・グラウンド一式。5年空き家の修繕は借主負担想定
    asis_repair: float = 2.0 * OKU         # 貸出前の最低限修繕（受変電・給排水・屋上防水）
    asis_cap: float = 0.07
    # 太陽光（屋外運動場4.2haのみ。建物敷地は解体費が地代を上回り、山林は林地開発0.5ha超で許可対象）
    solar_land_rent_m2: float = 200        # 円/㎡/年（地上設置の地代相場 150〜300円）
    solar_usable_rate: float = 0.85
    solar_cap: float = 0.06
    # 系統用蓄電池（必要面積は2〜3ha。特高接続前提）
    bess_area_m2: float = 25_000
    bess_land_rent_m2: float = 800         # 円/㎡/年
    bess_cap: float = 0.06
    # 産業用地（造成後に工場・倉庫用地として分譲）
    ind_sale_per_m2: float = 10_000        # 都市計画区域外・IC10分・丘陵地の分譲単価想定
    ind_site_works_per_m2: float = 4_000   # 整地・調整池・構内道路・給排水（既存平場前提）
    ind_sales_cost_rate: float = 0.05
    ind_margin: float = 0.15
    ind_months: int = 36
    # 山林保有（森林経営・J-クレジット等は無視）
    forest_value_m2: float = 100


def alt_uses(site: Site, cc: CommonCost, a: AltAssume) -> dict:
    out = {}
    # 現況一括賃貸
    noi = a.asis_rent_year - cc.property_tax_year()
    v = noi / a.asis_cap - a.asis_repair
    out["現況一括賃貸（研修・合宿・学校用途）"] = {"年間NOI": noi, "土地建物の収益価格": v, "備考": "開発許可不要。借主確保が前提"}
    # 太陽光（運動場のみ。建物はそのまま）
    rent = site.ground_m2 * a.solar_usable_rate * a.solar_land_rent_m2
    noi = rent - cc.property_tax_year()
    v = noi / a.solar_cap
    out["太陽光（運動場4.2haの地代・建物は残置）"] = {"年間NOI": noi, "土地建物の収益価格": v, "備考": "固都税を地代が辛うじて上回る水準。系統空き容量の確認要"}
    # 蓄電池
    rent = a.bess_area_m2 * a.bess_land_rent_m2
    noi = rent - cc.property_tax_year()
    v = noi / a.bess_cap
    out["系統用蓄電池（2.5ha地代・残地未利用）"] = {"年間NOI": noi, "土地建物の収益価格": v, "備考": "運動場の一部で成立。特高接続が前提で、DCと同じ電力論点"}
    # 産業用地分譲
    sales = site.flat_m2 * a.ind_sale_per_m2
    cost = cc.demolition(site.existing_gfa_m2) + site.flat_m2 * a.ind_site_works_per_m2 + sales * a.ind_sales_cost_rate
    cost += cc.property_tax_year() * a.ind_months / 12
    land = (sales / (1 + a.ind_margin) - cost) / (1 + cc.loan_rate * a.ind_months / 12) - 0.4 * OKU
    out["産業用地分譲（平場11haを工場・倉庫用地に）"] = {"年間NOI": 0.0, "土地建物の収益価格": land, "備考": f"売上{sales/OKU:.1f}億から解体・造成・利益15%を引いた残余。開発許可（1ha超）要"}
    # 山林
    out["山林・現況保有"] = {"年間NOI": -cc.property_tax_year(), "土地建物の収益価格": site.forest_m2 * a.forest_value_m2 + site.flat_m2 * a.forest_value_m2 * 5, "備考": "地目山林・原野の素地価格"}
    return out


# ---------------------------------------------------------------------------
# 6. 実行
# ---------------------------------------------------------------------------
def oku(v: float) -> str:
    return f"{v / OKU:,.1f}億"


def run(verbose: bool = True):
    site = Site()
    cc = CommonCost()
    scenarios = {
        "dc20": DCAssume(label="郊外型ミドル 20MW", it_mw=20, grid_connection=12 * OKU, site_works=4 * OKU),
        "dc50": DCAssume(label="郊外型ラージ 50MW", it_mw=50),
        "dc100": DCAssume(label="キャンパス型 100MW（平場11ha上限）", it_mw=100, grid_connection=40 * OKU, site_works=8 * OKU, construction_months=42),
    }
    results = {k: dc(site, cc, a) for k, a in scenarios.items()}

    # 感度1: 賃料 × capex（50MW・cap 5.0%）→ 開発利益率
    rents = [15_000, 18_000, 20_000, 22_000, 25_000]
    capexes = [16 * OKU, 20 * OKU, 24 * OKU]
    sens_rent_capex = []
    for r in rents:
        row = []
        for c in capexes:
            m = dc(site, cc, DCAssume(rent_per_kw_month=r, capex_per_mw=c)).metrics
            row.append(m["開発利益率(収益価格/総事業費-1)"])
        sens_rent_capex.append((r, row))

    # 感度2: cap × 賃料（50MW・capex 20億/MW）→ 含み損益
    caps = [0.045, 0.050, 0.055, 0.060]
    sens_cap_rent = []
    for cp in caps:
        row = []
        for r in rents:
            m = dc(site, cc, DCAssume(rent_per_kw_month=r, exit_cap=cp)).metrics
            row.append(m["含み損益(収益価格-総事業費)"])
        sens_cap_rent.append((cp, row))

    # 残余法（DC）: 規模 × 賃料
    residual = {}
    for k, a in scenarios.items():
        residual[a.label + "（賃料2.0万）"] = residual_land_dc(site, cc, a)
    residual["郊外型ラージ 50MW（賃料1.8万）"] = residual_land_dc(site, cc, DCAssume(rent_per_kw_month=18_000))
    residual["郊外型ラージ 50MW（賃料1.5万）"] = residual_land_dc(site, cc, DCAssume(rent_per_kw_month=15_000))
    residual["郊外型ラージ 50MW（賃料2.0万・cap6.0%・capex24億）"] = residual_land_dc(site, cc, DCAssume(exit_cap=0.06, capex_per_mw=24 * OKU))

    hold = holding_cost(site, cc)
    alts = alt_uses(site, cc, AltAssume())

    if verbose:
        print(f"敷地 {site.land_m2:,.0f}㎡ ({site.land_tsubo:,.0f}坪)  募集価格 {oku(site.asking_price)}  "
              f"{site.ask_per_m2:,.0f}円/㎡  平場換算 {site.ask_per_flat_m2:,.0f}円/㎡")
        print(f"平場 {site.flat_m2:,.0f}㎡ ({site.flat_m2/10_000:.1f}ha)  山林 {site.forest_m2:,.0f}㎡ ({site.forest_m2/10_000:.1f}ha)  既存建物 {site.existing_gfa_m2:,.0f}㎡")
        print(f"解体費 {oku(cc.demolition(site.existing_gfa_m2))}  固都税 {cc.property_tax_year()/MAN:,.0f}万円/年")
        print()
        for r in results.values():
            print(f"=== {r.name} ===")
            for kk, v in r.lines.items():
                print(f"  {kk:<18}{oku(v):>12}")
            print(f"  {'総事業費':<18}{oku(r.total_cost):>12}")
            for kk, v in r.metrics.items():
                if "利回り" in kk or "率" in kk or "比" in kk:
                    print(f"  {kk:<28}{v*100:>10.1f}%")
                elif "円/kW" in kk:
                    print(f"  {kk:<28}{v:>10,.0f}")
                elif "MW" in kk and "/" not in kk:
                    print(f"  {kk:<28}{v:>10,.1f}")
                else:
                    print(f"  {kk:<28}{oku(v):>12}")
            print()
        print("=== 感度: 開発利益率  行=賃料(円/kW/月), 列=capex(億/MW)  50MW・cap5.0% ===")
        print("賃料\\capex " + "".join(f"{c/OKU:>10.0f}億" for c in capexes))
        for r, row in sens_rent_capex:
            print(f"{r:>8,}   " + "".join(f"{v*100:>10.0f}%" for v in row))
        print()
        print("=== 感度: 含み損益(億)  行=cap, 列=賃料  50MW・capex20億/MW ===")
        print("cap\\賃料  " + "".join(f"{r:>10,}" for r in rents))
        for cp, row in sens_cap_rent:
            print(f"{cp*100:>6.1f}%   " + "".join(f"{v/OKU:>10.0f}" for v in row))
        print()
        print("=== 残余法: DC事業が土地に払える理論上限（開発利益15%控除後） ===")
        for k, v in residual.items():
            if v is None:
                print(f"  {k:<40}{'成立せず':>12}")
            else:
                print(f"  {k:<40}{oku(v):>12}  ({v/site.land_m2:,.0f}円/㎡)")
        print()
        print("=== 保有コスト（16.5億で取得し受電回答を待つ場合） ===")
        for y, yearly, cum, total in hold:
            print(f"  {y}年目  年額 {oku(yearly)}  累計 {oku(cum)}  簿価合計 {oku(total)}")
        print()
        print("=== DC以外の出口から見た土地建物の価格 ===")
        for k, v in alts.items():
            print(f"  {k:<36}{oku(v['土地建物の収益価格']):>10}  NOI {oku(v['年間NOI'])}  {v['備考']}")
    return site, cc, scenarios, results, sens_rent_capex, sens_cap_rent, residual, hold, alts, rents, capexes, caps


if __name__ == "__main__":
    run()
