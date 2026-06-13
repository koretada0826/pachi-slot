#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ジャグラー 設定推定エンジン  v0.1
==================================
店インテリジェンスの心臓部。
台の出玉履歴(総ゲーム数・BIG回数・REG回数)から、その台の設定を
ベイズ推定で当てる。全台・全日に回せば「店が土日に設定を入れるクセ」が見える。

■ 思想(今日の教訓を設計に埋め込む)
  - 「設定別の確率の数字」と「推定ロジック」を分離する。
  - 数字 = 差し替え可能な入力(無料ソースは食い違う。最終値は要・権威ソースで固定)。
  - ロジック = 不変の核(観測回数→設定の事後確率。これは数学なので正しい)。
  - こうすれば Garbage in しても「どこがGarbageか」が君に見える。

■ 使い方は2通り(同じエンジン)
  1) 終日データ(retrospective): 各台のフル稼働データ→設定推定→店のクセ集計【メイン】
  2) 実戦中(in-play): 打ちながら更新して、続行/ヤメを判断

■ 数字の出典と注意(2026-06 取得・★要検証★)
  下のDEFAULT表は jugglertopics.jp(マイジャグラーV) の値。
  ただし p-town/検索結果と設定6個別値・REG値が食い違う(監査で検出済)。
  → 実戦投入前に、サイトセブン等の権威データで必ず固定し直すこと。
  食い違い例: 設定6 BIG/REG が「同確率1/229.1」説 vs「1/219.0・1/240.9」説。
"""

from math import lgamma, log, exp

# ------------------------------------------------------------------
# 設定別 ボーナス確率(★要検証 placeholder: マイジャグラーV / jugglertopics)
#   prob = 1試行あたりの当選確率。 1/X の X を入れている。
# ------------------------------------------------------------------
MYJUGGLER_V = {
    # 設定: (BIG分母, REG分母)  出典: juggler7.com/my5/kaiseki.html
    # 監査: 設定1 REG=1/409.6 は p-town(単独+チェリー)と一致、設定6 BR=1:1(1/229.1)は
    #       既知の特徴&検索結果と一致 → 確定。前回のjugglertopics値は外れ値と判明し破棄。
    1: (273.1, 409.6),
    2: (270.8, 385.5),
    3: (266.4, 336.1),
    4: (254.0, 290.0),
    5: (240.1, 268.6),
    6: (229.1, 229.1),
}
SPEC_VERIFIED = True  # 3ソース照合済(juggler7 / p-town / 既知特徴)。2026-06-09 確定

# 機種名→設定別(BIG分母,REG分母)。アプリのJS MACHINESと同値。複数機種対応(2026-06-12)
SPECS = {
    "マイジャグラーV": MYJUGGLER_V,
    "ファンキージャグラー2KT": {1:(266.4,439.8),2:(259.0,407.1),3:(256.0,366.1),4:(249.2,322.8),5:(240.1,299.3),6:(219.9,262.1)},
    "ゴーゴージャグラー3":   {1:(259.0,354.2),2:(258.0,332.7),3:(257.0,306.2),4:(254.0,268.6),5:(247.3,247.3),6:(234.9,234.9)},
    "アイムジャグラーEX":   {1:(273.1,439.8),2:(269.7,399.6),3:(269.7,331.0),4:(259.0,315.1),5:(259.0,255.0),6:(255.0,255.0)},
    "ジャグラーガールズSS":  {1:(273.1,381.0),2:(270.8,350.5),3:(260.1,316.6),4:(250.1,281.3),5:(243.6,270.8),6:(226.0,252.1)},
    "ミスタージャグラー":    {1:(268.6,374.5),2:(267.5,354.2),3:(260.1,331.0),4:(249.2,291.3),5:(240.9,257.0),6:(237.4,237.4)},
    "ウルトラミラクルジャグラー":{1:(267.5,425.6),2:(261.1,402.1),3:(256.0,350.5),4:(242.7,322.8),5:(233.2,297.9),6:(216.3,277.7)},
    "ハッピージャグラーVIII":{1:(273.1,397.2),2:(270.8,362.1),3:(263.2,332.7),4:(254.0,300.6),5:(239.2,273.1),6:(226.0,256.0)},
}

def spec_for(machine_name):
    """週JSONのmachine名から該当スペックを返す(別名吸収)。無ければマイジャグVで代用。"""
    n = (machine_name or "").replace(" ", "")
    table = {"マイジャグラーV":"マイジャグラーV","ファンキージャグラー2KT":"ファンキージャグラー2KT",
             "ファンキージャグラー2":"ファンキージャグラー2KT","ゴーゴージャグラー3":"ゴーゴージャグラー3",
             "アイムジャグラーEX":"アイムジャグラーEX","ネオアイムジャグラーEX":"アイムジャグラーEX",
             "ジャグラーガールズSS":"ジャグラーガールズSS","ジャグラーガールズ":"ジャグラーガールズSS",
             "ミスタージャグラー":"ミスタージャグラー","ウルトラミラクルジャグラー":"ウルトラミラクルジャグラー",
             "ハッピージャグラーVIII":"ハッピージャグラーVIII","ハッピージャグラーV":"ハッピージャグラーVIII"}
    for k,v in table.items():
        if k.replace(" ","") in n:
            return SPECS[v]
    return MYJUGGLER_V


def _poisson_logpmf(k: int, lam: float) -> float:
    """Poisson(λ) で k 回観測される対数確率。lam>0。"""
    if lam <= 0:
        return -1e18 if k > 0 else 0.0
    return k * log(lam) - lam - lgamma(k + 1)


def estimate(games: int, big: int, reg: int,
             spec: dict = MYJUGGLER_V,
             prior: dict | None = None) -> dict:
    """
    観測(総ゲーム数 games, BIG回数 big, REG回数 reg)から設定の事後確率を返す。

    prior: 設定->事前確率 の辞書。Noneなら一様。
           ★店インテリジェンスで「この店は6を入れにくい」が分かれば
             prior に反映する。A層(事前)→B層(観測で更新)のパイプライン。
    返り値: {設定: 事後確率}, および要約。
    """
    if prior is None:
        prior = {s: 1.0 / len(spec) for s in spec}

    log_post = {}
    for s, (big_den, reg_den) in spec.items():
        lam_big = games / big_den
        lam_reg = games / reg_den
        ll = _poisson_logpmf(big, lam_big) + _poisson_logpmf(reg, lam_reg)
        log_post[s] = log(prior[s]) + ll

    # 正規化(対数空間で安定化)
    m = max(log_post.values())
    unnorm = {s: exp(v - m) for s, v in log_post.items()}
    z = sum(unnorm.values())
    post = {s: unnorm[s] / z for s in spec}
    return post


def summarize(games: int, big: int, reg: int,
              spec: dict = MYJUGGLER_V, prior: dict | None = None) -> str:
    post = estimate(games, big, reg, spec, prior)
    best = max(post, key=post.get)
    p_high = post[5] + post[6]      # 設定5以上(高設定)
    p_six = post[6]
    big_p = f"1/{games/big:.1f}" if big else "0回"
    reg_p = f"1/{games/reg:.1f}" if reg else "0回"
    lines = [
        f"入力: {games:,}G  BIG {big}回({big_p})  REG {reg}回({reg_p})",
        "設定別 事後確率:",
    ]
    for s in sorted(spec):
        bar = "█" * round(post[s] * 30)
        lines.append(f"  設定{s}: {post[s]*100:5.1f}%  {bar}")
    lines.append(f"→ 最有力: 設定{best}   高設定(5-6)確率: {p_high*100:.1f}%   設定6: {p_six*100:.1f}%")
    if not SPEC_VERIFIED:
        lines.append("⚠ 設定別確率は未検証(要・権威ソースで固定)。推定値は暫定。")
    return "\n".join(lines)


if __name__ == "__main__":
    print("=== ジャグラー設定推定エンジン v0.1 (マイジャグV・★数値要検証) ===\n")

    # サンプル:終日8000G・高設定っぽい台
    print("【例1】8000G / BIG35 / REG33  (REGが軽い=高設定の匂い)")
    print(summarize(8000, 35, 33))
    print()
    # サンプル:終日8000G・低設定っぽい台
    print("【例2】8000G / BIG28 / REG18  (REGが重い=低設定の匂い)")
    print(summarize(8000, 28, 18))
    print()
    # サンプル:朝の少回転(まだ判別できないはず)
    print("【例3】1200G / BIG6 / REG5  (回転少=まだ判別不能のはず)")
    print(summarize(1200, 6, 5))
