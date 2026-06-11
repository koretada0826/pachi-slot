#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バジリスク絆2  天井狙い 期待値・判断ツール  v0.1
================================================

立ち位置(正直版):
  - 天井狙いの期待値は「公開情報」で、複数サイトが同じ数字を出している。
    秘密の計算で差はつかない。差別化は実行(速さ・交換率補正・規律)だけ。
  - よってこのツールは「物理を再現する模型」ではなく、
    複数サイトで照合済みの公開期待値表を encode して、
    実戦で「打つ/スルー」を即判断するための道具。
  - 精度の根拠 = 公開表のサイト間一致。捏造値は入れていない。

データ出典(すべて無料公開・2026-06取得):
  - 期待値表(等価): nyon777.com/kitaichi/ha/bk2/
  - コイン持ち 50枚/49.5G, BT平均415.5枚, AT純増2.9枚/G: tsuranuki-method.com
  - 天井800G+前兆 / コイン持ち約50G: p-town.dmm.com/specials/2326, slotjin.com
  注) BT平均枚数は slotjin と tsuranuki が共に 415.5枚 で一致(照合済み)。

未解決・要注意(誇張しないための明記):
  1. 下表は【等価交換】専用。非等価(5.6枚等)は別テーブルが必要。
     ここでは近似補正を出すが「要検証」。鵜呑み禁止。
  2. スルー回数(0〜6スルー)加味の期待値は別軸。本v0.1はゲーム数のみ。
  3. 実戦では「座れる前提」。奪い合いで座れなければEVは実現しない。
"""

# ------------------------------------------------------------------
# 公開期待値表(等価交換, 円)  出典: nyon777  ※サイト間照合のスペックと整合
#   現在ゲーム数 -> その地点から打ち始めた場合の期待値(円)
# ------------------------------------------------------------------
EV_TABLE_TOUKA = {
    0:  -980,
    50: -502,
    100: -96,
    150: 317,
    200: 673,
    250: 1024,
    300: 1388,
    350: 1760,
    400: 2240,
    450: 2635,
    500: 2977,
    550: 3372,
    600: 3740,
    650: 4242,
    700: 4793,
    750: 5236,
}

CEILING_G = 800          # ゲーム数天井(+前兆)
COIN_HOLD_G_PER_50 = 49.5  # 50枚あたりのゲーム数(コイン持ち)
BT_AVG_COINS = 415.5     # BT平均獲得枚数


def ev_touka(current_g: float) -> float:
    """等価交換での期待値(円)を線形補間で返す。"""
    if current_g < 0:
        raise ValueError("ゲーム数は0以上")
    if current_g >= CEILING_G:
        # 天井到達済みは前兆待ちで実質確定域。最大値で頭打ち表示。
        return EV_TABLE_TOUKA[750] + (current_g - 750) * (
            (EV_TABLE_TOUKA[750] - EV_TABLE_TOUKA[700]) / 50.0)
    keys = sorted(EV_TABLE_TOUKA)
    # current_g を挟む2点で線形補間
    for i in range(len(keys) - 1):
        lo, hi = keys[i], keys[i + 1]
        if lo <= current_g <= hi:
            t = (current_g - lo) / (hi - lo)
            return EV_TABLE_TOUKA[lo] + t * (EV_TABLE_TOUKA[hi] - EV_TABLE_TOUKA[lo])
    return EV_TABLE_TOUKA[keys[-1]]


def ev_adjusted(current_g: float, koukan_per_50: float = 50.0) -> dict:
    """
    交換率を加味した期待値(近似)。
    koukan_per_50: 換金時、50枚=何円か。等価(20円/枚)=1000。
                   5.6枚交換(約17.86円/枚)=約 893。
    【重要】非等価の補正は近似。報酬側のみ縮める粗いモデル。要・実表検証。
    """
    base = ev_touka(current_g)          # 等価のEV
    touka_50 = 1000.0                   # 等価: 50枚=1000円
    if abs(koukan_per_50 - touka_50) < 1e-6:
        return {"ev": round(base), "approx": False, "note": "等価・公開表ベース"}

    # 近似: BT当たりで得た出玉の換金ギャップだけEVを下げる。
    # ざっくり「天井までに当たるBT回数 ~ (期待値+投資)/BT価値」で逆算せず、
    # 保守的に BT平均枚数 1回ぶんの換金ギャップを上限として効かせる近似。
    gap_per_coin = (touka_50 - koukan_per_50) / 50.0   # 1枚あたりの目減り円
    # 期待出玉枚数 ~ (等価EV + 想定投資) / 20。粗い近似なので係数は控えめ。
    approx_payout_coins = max(0.0, (base + (CEILING_G - current_g) * (50.0 / COIN_HOLD_G_PER_50) * 20.0) / 20.0)
    penalty = approx_payout_coins * gap_per_coin
    return {
        "ev": round(base - penalty),
        "approx": True,
        "note": f"非等価 近似(要検証): 等価EV {round(base)}円 − 換金ペナ約 {round(penalty)}円",
    }


def judge(current_g: float, koukan_per_50: float = 50.0,
          border_yen: int = 0) -> str:
    """打つ/スルーの判定文字列を返す。border_yen 以上で『打つ』。"""
    r = ev_adjusted(current_g, koukan_per_50)
    ev = r["ev"]
    mark = "打つ ◎" if ev >= border_yen + 500 else ("微妙 △" if ev >= border_yen else "スルー ×")
    lines = [
        f"現在G: {current_g:.0f}  /  天井: {CEILING_G}G",
        f"期待値: {ev:+,} 円   → {mark}",
        f"判定基準: {border_yen:+,}円以上で参加 (+500以上で◎)",
        f"備考: {r['note']}",
    ]
    if r["approx"]:
        lines.append("⚠ 非等価の数値は近似。実戦前に5.6枚交換の公開表で要照合。")
    lines.append("⚠ スルー回数は未加味(v0.1)。6スルー域は別途上振れ。")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    print("=== バジリスク絆2 天井期待値ツール v0.1 (等価ベース) ===\n")
    print("公開期待値表(等価) 抜粋:")
    for g in (0, 100, 200, 300, 400, 500, 600, 700):
        print(f"  {g:>3}G  ->  {ev_touka(g):+,.0f}円")
    print()
    if len(sys.argv) >= 2:
        g = float(sys.argv[1])
        kk = float(sys.argv[2]) if len(sys.argv) >= 3 else 50.0
        kk_50 = 1000.0 if kk == 50.0 else kk
        print(judge(g, kk_50))
    else:
        print("使い方:  python3 kizuna2_ev.py <現在ゲーム数> [換金時50枚=何円(等価は1000)]")
        print("例:      python3 kizuna2_ev.py 350")
        print("例(5.6枚): python3 kizuna2_ev.py 350 893")
