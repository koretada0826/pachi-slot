#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
みんレポ 汎用スクレイパー  v0.1
=================================
店選びの全データ取得エンジン。
指定した店のタグページから全日付を集め、各日付ページの
「機種ごとの 平均差枚 / 平均G数 / 勝率 / 出率」を全部取る。

方針(今日の結論):
  - 人の解釈(ランキング・おすすめ)は無視。生データ(出率)だけを全店ぶん取る。
  - 出率は「その機種のその日の全台平均」。100%超=客が勝った=設定が入った疑い。
  - これを店×機種×日付パターン(特定日/曜日)で集計 → 店選びに使う。

出典: min-repo.com (無料・過去ログ2024〜保存)
注意: 礼儀としてsleepを入れる。差枚/G/出率のみでBB/REGは無い(粗い層)。
"""
import re, json, time, os, sys
import urllib.request

HALLS = {
    "TOHO池袋":        "https://min-repo.com/tag/toho%E6%B1%A0%E8%A2%8B%E5%BA%97/",
    "YASUDA9":         "https://min-repo.com/tag/%E3%82%84%E3%81%99%E3%81%A0%E6%9D%B1%E6%B1%A0%E8%A2%8B9%E5%8F%B7%E5%BA%97/",
    "マルハン池袋":     "https://min-repo.com/tag/%E3%83%9E%E3%83%AB%E3%83%8F%E3%83%B3%E6%B1%A0%E8%A2%8B%E5%BA%97/",
    "マルハンSLOTBASE": "https://min-repo.com/tag/%E3%83%9E%E3%83%AB%E3%83%8F%E3%83%B3%E6%B1%A0%E8%A2%8Bslot-base/",
}

UA = {'User-Agent': 'Mozilla/5.0'}
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 各日付ページの機種行: 機種名 / 平均差枚 / 平均G / 勝率 / 出率%
ROW = re.compile(
    r'kishu=[^"]*">([^<]+)</a></td>\s*'
    r'<td class="samai_cell">(-?[\d,]+)</td>\s*'
    r'<td>([\d,]+)</td>\s*'
    r'<td>([^<]*)</td>\s*'
    r'<td class="samai_cell _deritsu">([\d.]+)%'
)
LINK = re.compile(r'href="(https://min-repo\.com/\d+/)">(\d{1,2})/(\d{1,2})\(')


def get(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=20
    ).read().decode('utf-8', 'replace')


def collect_dates(tag_url, max_pages=15):
    """タグページを辿り (url, month, day) を集める。"""
    pairs = {}
    for p in range(1, max_pages + 1):
        url = tag_url if p == 1 else f"{tag_url}page/{p}/"
        try:
            html = get(url)
        except Exception:
            break
        found = LINK.findall(html)
        new = 0
        for u, mm, dd in found:
            if u not in pairs:
                pairs[u] = (int(mm), int(dd)); new += 1
        if new == 0 and p > 1:
            break
        time.sleep(0.3)
    return pairs


def scrape_hall(name, tag_url, max_dates=160):
    pairs = collect_dates(tag_url)
    # 新しい順に上限まで(辞書挿入順=新しい順に近い)
    items = list(pairs.items())[:max_dates]
    rows = []
    for i, (u, (mm, dd)) in enumerate(items):
        try:
            html = get(u)
        except Exception:
            continue
        for kishu, samai, g, win, deri in ROW.findall(html):
            rows.append({
                "m": mm, "d": dd, "kishu": kishu.strip(),
                "samai": int(samai.replace(',', '')),
                "g": int(g.replace(',', '')),
                "deri": float(deri),
            })
        time.sleep(0.15)
        if i % 25 == 0:
            print(f"  [{name}] {i}/{len(items)} dates, {len(rows)} rows", flush=True)
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, f"{name}.json")
    json.dump({"hall": name, "rows": rows}, open(path, 'w'), ensure_ascii=False)
    print(f"  [{name}] DONE: {len(items)} dates, {len(rows)} rows -> {path}", flush=True)
    return len(rows)


if __name__ == "__main__":
    targets = sys.argv[1:] or list(HALLS)
    for name in targets:
        if name not in HALLS:
            print("unknown hall:", name); continue
        print(f"=== scraping {name} ===", flush=True)
        scrape_hall(name, HALLS[name])
    print("ALL DONE", flush=True)
