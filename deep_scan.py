#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上位候補を深く取り直す(60日)。日付パターン(行くべき日)を確定するため。"""
import re, json, os, time, urllib.parse
from corridor_scan import get, LINK, ROW, OUTDIR, SLEEP

TARGETS = ["ジュラク王子店", "マルハン池袋店"]
CATS = [("東京都","北区"), ("東京都","豊島区")]
DEEP_DATES = 60


def discover():
    found = {}
    for pref, city in CATS:
        url = f"https://min-repo.com/category/{urllib.parse.quote(pref)}/{urllib.parse.quote(city)}/"
        html = get(url)
        for u, name in re.findall(r'href="(https://min-repo\.com/tag/[^"]+)"[^>]*>([^<]+)</a>', html):
            found[name.strip()] = u
        time.sleep(SLEEP)
    return found


def scrape(name, tag):
    pairs = {}
    for p in range(1, 8):
        html = get(tag if p == 1 else f"{tag}page/{p}/")
        new = 0
        for u, m, d in LINK.findall(html):
            if u not in pairs:
                pairs[u] = (int(m), int(d)); new += 1
        if new == 0 and p > 1:
            break
        time.sleep(SLEEP)
    rows = []
    for i, (u, (m, d)) in enumerate(list(pairs.items())[:DEEP_DATES]):
        html = get(u)
        for k, s, g, w, de in ROW.findall(html):
            rows.append({"m": m, "d": d, "kishu": k.strip(),
                         "samai": int(s.replace(',', '')), "g": int(g.replace(',', '')), "deri": float(de)})
        time.sleep(SLEEP)
        if i % 15 == 0:
            print(f"  [{name}] {i}/{min(len(pairs),DEEP_DATES)} dates, {len(rows)} rows", flush=True)
    json.dump({"hall": name, "rows": rows}, open(os.path.join(OUTDIR, f"{name}_deep.json"), 'w'), ensure_ascii=False)
    print(f"  [{name}] DEEP DONE {len(rows)} rows", flush=True)


if __name__ == "__main__":
    halls = discover()
    for t in TARGETS:
        if t in halls:
            print(f"=== deep {t} ===", flush=True)
            scrape(t, halls[t])
        else:
            print(f"見つからず: {t}", flush=True)
    print("ALL DEEP DONE", flush=True)
