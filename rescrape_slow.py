#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
レート制限対応・低速再取得  v0.1
TOHOの大量取得でmin-repoにブロックされたので、
(1)解除を見張り (2)解除後にゆっくり 残り店を取得する。
"""
import re, json, os, time, urllib.request, urllib.parse

UA = {'User-Agent': 'Mozilla/5.0'}
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TOSHIMA = "https://min-repo.com/category/%E6%9D%B1%E4%BA%AC%E9%83%BD/%E8%B1%8A%E5%B3%B6%E5%8C%BA/"

ROW = re.compile(
    r'kishu=[^"]*">([^<]+)</a></td>\s*<td class="samai_cell">(-?[\d,]+)</td>\s*'
    r'<td>([\d,]+)</td>\s*<td>([^<]*)</td>\s*<td class="samai_cell _deritsu">([\d.]+)%')
LINK = re.compile(r'href="(https://min-repo\.com/\d+/)">(\d{1,2})/(\d{1,2})\(')


def get_raw(url, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode('utf-8', 'replace')


def get(url, tries=4, pause=2.0):
    """空ボディ(レート制限)ならリトライ。"""
    for t in range(tries):
        try:
            html = get_raw(url)
            if len(html) > 500:
                return html
        except Exception:
            pass
        time.sleep(pause * (t + 1))
    return ""


def wait_unblock(max_min=40):
    """TOPが中身を返すまで60sごとに見張る。"""
    for i in range(max_min):
        try:
            if len(get_raw("https://min-repo.com/")) > 500:
                print(f"unblocked after ~{i} min", flush=True); return True
        except Exception:
            pass
        time.sleep(60)
    return False


def discover_tags():
    html = get(TOSHIMA)
    tags = list(dict.fromkeys(re.findall(r'href="(https://min-repo\.com/tag/[^"]+)"', html)))
    want = {}
    for u in tags:
        dec = urllib.parse.unquote(u)
        if "やすだ" in dec or "yasuda" in dec.lower() or "YASUDA" in dec:
            want.setdefault("YASUDA9", u)
        if "マルハン" in dec and "slot-base" in dec.lower():
            want["マルハンSLOTBASE"] = u
        elif "マルハン" in dec:
            want.setdefault("マルハン池袋", u)
    return want


def scrape(name, tag, max_dates=150, sleep=2.0):
    pairs = {}
    for p in range(1, 15):
        url = tag if p == 1 else f"{tag}page/{p}/"
        html = get(url)
        found = LINK.findall(html)
        new = sum(1 for u, m, d in found if u not in pairs)
        for u, m, d in found:
            pairs.setdefault(u, (int(m), int(d)))
        if new == 0 and p > 1:
            break
        time.sleep(sleep)
    rows = []
    for i, (u, (m, d)) in enumerate(list(pairs.items())[:max_dates]):
        html = get(u)
        for k, s, g, w, de in ROW.findall(html):
            rows.append({"m": m, "d": d, "kishu": k.strip(),
                         "samai": int(s.replace(',', '')), "g": int(g.replace(',', '')),
                         "deri": float(de)})
        time.sleep(sleep)
        if i % 20 == 0:
            print(f"  [{name}] {i}/{len(pairs)} dates, {len(rows)} rows", flush=True)
    os.makedirs(OUTDIR, exist_ok=True)
    json.dump({"hall": name, "rows": rows}, open(os.path.join(OUTDIR, f"{name}.json"), 'w'), ensure_ascii=False)
    print(f"  [{name}] DONE {len(rows)} rows", flush=True)


if __name__ == "__main__":
    print("待機: ブロック解除を見張る...", flush=True)
    if not wait_unblock():
        print("解除されず。後で再実行を。", flush=True); raise SystemExit(1)
    tags = discover_tags()
    print("発見タグ:", {k: urllib.parse.unquote(v) for k, v in tags.items()}, flush=True)
    for name, tag in tags.items():
        print(f"=== {name} ===", flush=True)
        scrape(name, tag)
    print("ALL DONE", flush=True)
