#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
埼京線回廊+池袋 包括スクリーニング  v0.1
==========================================
浮間舟渡方面(埼京線)の穴場を含め、店を広く拾って店選びする。
カテゴリ(市区)から店を自動列挙し、低速(レート制限回避)で各店を
スクリーニング取得(直近~20日)。出率で店をランク付けして
「甘い店・穴場」を炙り出す。深掘りは上位店だけ後で。

レート制限対策: TOPで解除を見張り、各リクエスト3秒間隔、空ボディはリトライ。
"""
import re, json, os, time, urllib.request, urllib.parse

UA = {'User-Agent': 'Mozilla/5.0'}
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SLEEP = 3.0
SCREEN_DATES = 15  # スクリーニングは直近15日(4Gのギガ節約)

CATEGORIES = {
    "戸田市": ("埼玉県", "戸田市"),
    "北区":   ("東京都", "北区"),
}

ROW = re.compile(
    r'kishu=[^"]*">([^<]+)</a></td>\s*<td class="samai_cell">(-?[\d,]+)</td>\s*'
    r'<td>([\d,]+)</td>\s*<td>([^<]*)</td>\s*<td class="samai_cell _deritsu">([\d.]+)%')
LINK = re.compile(r'href="(https://min-repo\.com/\d+/)">(\d{1,2})/(\d{1,2})\(')


def get_raw(url, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode('utf-8', 'replace')


def get(url, tries=5):
    for t in range(tries):
        try:
            h = get_raw(url)
            if len(h) > 500:
                return h
        except Exception:
            pass
        time.sleep(SLEEP * (t + 1))
    return ""


def wait_unblock(max_checks=48, interval=240):
    """解除を辛抱強く見張る(既定: 4分間隔×48回 = 約3.2時間)。"""
    for i in range(max_checks):
        try:
            if len(get_raw("https://min-repo.com/")) > 500:
                print(f"unblocked after ~{i*interval//60}min", flush=True); return True
        except Exception:
            pass
        print(f"  still blocked... check {i+1}/{max_checks}", flush=True)
        time.sleep(interval)
    return False


def cat_url(pref, city):
    return f"https://min-repo.com/category/{urllib.parse.quote(pref)}/{urllib.parse.quote(city)}/"


def discover_halls(pref, city):
    """カテゴリページから (店名, タグURL) を列挙。"""
    html = get(cat_url(pref, city))
    tags = re.findall(r'href="(https://min-repo\.com/tag/[^"]+)"[^>]*>([^<]+)</a>', html)
    out = {}
    for u, name in tags:
        name = name.strip()
        if name and u not in out.values():
            out[name] = u
    # 名前が取れない場合のフォールバック
    if not out:
        for u in dict.fromkeys(re.findall(r'href="(https://min-repo\.com/tag/[^"]+)"', html)):
            out[urllib.parse.unquote(u).split('/tag/')[-1].strip('/')] = u
    return out


def scrape(name, tag, max_dates=SCREEN_DATES):
    safe = re.sub(r'[/\\]', '_', name)
    path = os.path.join(OUTDIR, f"{safe}.json")
    if os.path.exists(path):
        print(f"  skip(既存): {name}", flush=True); return
    pairs = {}
    for p in range(1, 4):  # スクリーニングはタグ3ページまで
        html = get(tag if p == 1 else f"{tag}page/{p}/")
        found = LINK.findall(html)
        new = sum(1 for u, m, d in found if u not in pairs)
        for u, m, d in found:
            pairs.setdefault(u, (int(m), int(d)))
        if new == 0 and p > 1:
            break
        time.sleep(SLEEP)
    rows = []
    for u, (m, d) in list(pairs.items())[:max_dates]:
        html = get(u)
        for k, s, g, w, de in ROW.findall(html):
            rows.append({"m": m, "d": d, "kishu": k.strip(),
                         "samai": int(s.replace(',', '')), "g": int(g.replace(',', '')), "deri": float(de)})
        time.sleep(SLEEP)
    os.makedirs(OUTDIR, exist_ok=True)
    json.dump({"hall": name, "rows": rows}, open(path, 'w'), ensure_ascii=False)
    print(f"  DONE {name}: {len(pairs)} dates, {len(rows)} rows", flush=True)


if __name__ == "__main__":
    print("解除待ち...", flush=True)
    if not wait_unblock():
        print("解除されず終了", flush=True); raise SystemExit(1)
    halls = {}
    for label, (pref, city) in CATEGORIES.items():
        d = discover_halls(pref, city)
        print(f"[{label}] {len(d)}店: {list(d)}", flush=True)
        halls.update(d)
        time.sleep(SLEEP)
    print(f"=== 合計 {len(halls)} 店をスクリーニング ===", flush=True)
    for i, (name, tag) in enumerate(halls.items()):
        print(f"({i+1}/{len(halls)}) {name}", flush=True)
        try:
            scrape(name, tag)
        except Exception as e:
            print(f"  ERR {name}: {e}", flush=True)
    print("ALL DONE", flush=True)
