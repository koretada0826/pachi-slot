#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
店選び分析  v0.1
=================
minrepo_scraper.py が集めた生データ(data/*.json)から、
「どの店が・どの機種で・どの日付パターンで甘いか」を炙り出す。

指標:
  - 出率(その機種のその日の全台平均)。100%超=客が勝った=設定が入った疑い。
  - 店ごとに、ジャグラー系の 平均出率 / 100%超の割合 を出して店をランク付け。
  - 日付パターン(4の日/7の日/ゾロ目/月末…)別に、平均出率を平常日と比較。
    → 「生きてる旧イベ」を相対比較で検出(設定別確率の数字は不要=ノイズに強い)。

整合性:
  - G数1000未満は除外(回転少=ノイズ)。
  - サンプル数Nを必ず表示。Nが小さい差は「方向性」止まりと明記。
  - diff/SE で粗い有意性(|z|>2で★)。断定はしない。
"""
import json, os, glob, math

DATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MIN_G = 1000

PATTERNS = {
    "1のつく日": lambda d: d in (1, 11, 21, 31),
    "3のつく日": lambda d: d in (3, 13, 23),
    "4のつく日": lambda d: d in (4, 14, 24),
    "5のつく日": lambda d: d in (5, 15, 25),
    "7のつく日": lambda d: d in (7, 17, 27),
    "ゾロ目":     lambda d: d in (11, 22),
    "月末(28-31)": lambda d: d >= 28,
}


def load():
    halls = {}
    for path in glob.glob(os.path.join(DATADIR, "*.json")):
        obj = json.load(open(path, encoding='utf-8'))
        halls[obj["hall"]] = obj["rows"]
    return halls


def is_juggler(kishu):
    return "ジャグラー" in kishu


def mean_std(xs):
    n = len(xs)
    if n == 0:
        return 0, 0, 0
    m = sum(xs) / n
    if n == 1:
        return m, 0, 1
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(var), n


def hall_summary(rows):
    jug = [r for r in rows if is_juggler(r["kishu"]) and r["g"] >= MIN_G]
    deris = [r["deri"] for r in jug]
    m, sd, n = mean_std(deris)
    over = sum(1 for r in jug if r["deri"] >= 100) / n * 100 if n else 0
    return {"n": n, "mean_deri": m, "over100": over,
            "samai": sum(r["samai"] for r in jug) / n if n else 0}


def pattern_analysis(rows):
    jug = [r for r in rows if is_juggler(r["kishu"]) and r["g"] >= MIN_G]
    out = []
    for label, fn in PATTERNS.items():
        ev = [r["deri"] for r in jug if fn(r["d"])]
        base = [r["deri"] for r in jug if not fn(r["d"])]
        me, se, ne = mean_std(ev)
        mb, sb, nb = mean_std(base)
        if ne < 3 or nb < 3:
            continue
        se_diff = math.sqrt((se ** 2 / ne) + (sb ** 2 / nb)) or 1e-9
        z = (me - mb) / se_diff
        out.append((label, ne, me, mb, me - mb, z))
    out.sort(key=lambda x: -x[4])
    return out


def main():
    halls = load()
    if not halls:
        print("データがまだありません(スクレイプ完了待ち)"); return

    print("=" * 64)
    print("【店ランキング】ジャグラー系・平均出率(G≥1000)")
    print("=" * 64)
    ranked = sorted(halls.items(),
                    key=lambda kv: -hall_summary(kv[1])["mean_deri"])
    for name, rows in ranked:
        s = hall_summary(rows)
        print(f"  {name:16s}  平均出率 {s['mean_deri']:5.1f}%  "
              f"100%超 {s['over100']:4.1f}%  平均差枚 {s['samai']:+6.0f}  (N={s['n']})")

    print()
    for name, rows in ranked:
        pa = pattern_analysis(rows)
        print(f"--- {name}:日付パターン別 出率(ジャグラー系) ---")
        if not pa:
            print("   データ不足"); continue
        for label, n, me, mb, diff, z in pa:
            star = " ★" if abs(z) > 2 else ""
            arrow = "↑甘い" if diff > 0 else "↓渋い"
            print(f"   {label:10s} N={n:3d}  該当日 {me:5.1f}% vs 他 {mb:5.1f}%  "
                  f"差{diff:+5.1f} {arrow} (z={z:+.1f}){star}")
        print()
    print("注: ★=|z|>2(粗い有意)。Nが小さい差は方向性止まり。出率は店全体平均で、")
    print("    設定は一部台に集中しうる(平均は薄まる)。最終確認は精密層(BB/REG)で。")


if __name__ == "__main__":
    main()
