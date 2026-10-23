#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦卡路里 · 麦门周报卡片生成器

读取本地账本与画像，生成麦当劳品牌风格的自包含 HTML 周报卡片（无外部依赖，可直接打开/截图分享）。

用法:
    python weekly_report.py [ledger.json] [profile.json] [-o output.html]

默认路径:
    ledger:  ~/.workbuddy/skills-data/maikaluli/ledger.json
    profile: ~/.workbuddy/skills-data/maikaluli/profile.json

ledger.json 格式:
{
  "entries": [
    {"date": "2026-10-23", "source": "order|manual",
     "items": [{"name": "麦香鸡", "qty": 1, "kcal": 369, "protein": 15, "fat": 17, "carb": 39}],
     "amount": 27.0}
  ]
}

配色: 薯条红 #DA291C / 金拱黄 #FFC72C / 白底圆角卡片。
"""

import json
import os
import sys
from datetime import date, timedelta

MCD_RED = "#DA291C"
MCD_YELLOW = "#FFC72C"
MCD_DARK = "#27251F"


def load_json(path: str, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def bar_chart(days: list, target: float) -> str:
    """7 天柱状图 + 目标虚线。days: [(label, kcal), ...]"""
    W, H, pad = 560, 200, 36
    maxv = max([target * 1.3] + [v for _, v in days]) or 1
    bw = (W - pad * 2) / 7 * 0.55
    step = (W - pad * 2) / 7
    ty = H - pad - (target / maxv) * (H - pad * 2)
    parts = [
        f'<line x1="{pad}" y1="{ty:.1f}" x2="{W-pad}" y2="{ty:.1f}" stroke="{MCD_RED}" stroke-width="2" stroke-dasharray="6,5"/>',
        f'<text x="{W-pad+4}" y="{ty+4:.1f}" font-size="12" fill="{MCD_RED}" font-weight="700">目标 {int(target)}</text>',
    ]
    for i, (label, v) in enumerate(days):
        x = pad + step * i + (step - bw) / 2
        h = (v / maxv) * (H - pad * 2)
        y = H - pad - h
        over = v > target
        color = MCD_RED if over else MCD_YELLOW
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="6" fill="{color}"/>')
        if v > 0:
            parts.append(f'<text x="{x + bw/2:.1f}" y="{y - 6:.1f}" font-size="12" text-anchor="middle" fill="{MCD_DARK}" font-weight="700">{int(v)}</text>')
        parts.append(f'<text x="{x + bw/2:.1f}" y="{H - pad + 18:.1f}" font-size="12" text-anchor="middle" fill="#8a8577">{label}</text>')
    return f'<svg viewBox="0 0 {W+70} {H+10}" style="width:100%">{" ".join(parts)}</svg>'


def donut(p: float, f: float, c: float) -> str:
    """三大营养素环图。"""
    total = (p + f + c) or 1
    segs = [("蛋白质", p, MCD_RED), ("脂肪", f, MCD_YELLOW), ("碳水", c, MCD_DARK)]
    cx, cy, r, sw = 90, 90, 62, 26
    parts = []
    start = -90.0
    import math
    for name, v, color in segs:
        frac = v / total
        if frac <= 0:
            continue
        end = start + frac * 360
        large = 1 if (end - start) > 180 else 0
        x1, y1 = cx + r * math.cos(math.radians(start)), cy + r * math.sin(math.radians(start))
        x2, y2 = cx + r * math.cos(math.radians(end)), cy + r * math.sin(math.radians(end))
        parts.append(f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="{sw}" fill="none"/>')
        start = end
    legend = " ".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:6px 0;font-size:14px">'
        f'<span style="width:12px;height:12px;border-radius:4px;background:{color};display:inline-block"></span>'
        f'{name} <b>{v:.0f}g</b> <span style="color:#8a8577">{v/total*100:.0f}%</span></div>'
        for name, v, color in segs)
    svg = (f'<svg viewBox="0 0 180 180" style="width:150px;flex:none">{"".join(parts)}'
           f'<text x="90" y="86" text-anchor="middle" font-size="13" fill="#8a8577">本周累计</text>'
           f'<text x="90" y="108" text-anchor="middle" font-size="20" font-weight="800" fill="{MCD_DARK}">{p+f+c:.0f}g</text></svg>')
    return f'<div style="display:flex;align-items:center;gap:18px">{svg}<div>{legend}</div></div>'


def render(ledger: dict, profile: dict) -> str:
    entries = [e for e in ledger.get("entries", []) if e.get("items")]
    target = float(profile.get("calorie_target", 600))
    today = date.today()
    week = [(today - timedelta(days=6 - i)) for i in range(7)]
    by_date = {}
    for e in entries:
        d = e.get("date", "")
        agg = by_date.setdefault(d, {"kcal": 0, "amount": 0.0, "protein": 0, "fat": 0, "carb": 0, "items": {}})
        for it in e["items"]:
            q = it.get("qty", 1)
            agg["kcal"] += it.get("kcal", 0) * q
            agg["protein"] += it.get("protein", 0) * q
            agg["fat"] += it.get("fat", 0) * q
            agg["carb"] += it.get("carb", 0) * q
            agg["items"][it["name"]] = agg["items"].get(it["name"], 0) + q
        agg["amount"] += float(e.get("amount", 0))

    days = [(f"{d.month}/{d.day}", by_date.get(d.isoformat(), {}).get("kcal", 0)) for d in week]
    total_kcal = sum(v for _, v in days)
    active = sum(1 for _, v in days if v > 0)
    total_amount = sum(a.get("amount", 0) for a in by_date.values())
    tp = sum(a["protein"] for a in by_date.values())
    tf = sum(a["fat"] for a in by_date.values())
    tc = sum(a["carb"] for a in by_date.values())
    item_count = {}
    for a in by_date.values():
        for n, q in a["items"].items():
            item_count[n] = item_count.get(n, 0) + q
    top_items = sorted(item_count.items(), key=lambda x: -x[1])[:5]
    over_days = sum(1 for _, v in days if v > target)

    top_html = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:10px 4px;border-bottom:1px dashed #eee">'
        f'<span>{"🥇🥈🥉"[i] if i < 3 else "·"} {n}</span><b>×{q}</b></div>'
        for i, (n, q) in enumerate(top_items)) or '<div style="color:#8a8577;padding:12px 0">本周还没有记录，从下一单开始积累吧</div>'

    verdict = "保持得不错，继续 💪" if over_days == 0 and active > 0 else (
        f"有 {over_days} 天超过目标，下周帮你收紧一点" if over_days else "本周数据还很少，吃起来再回来看")

    def stat(num, unit, label, color=MCD_DARK):
        return (f'<div style="flex:1;background:#fff;border-radius:16px;padding:18px 8px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.05)">'
                f'<div style="font-size:30px;font-weight:800;color:{color}">{num}<span style="font-size:13px;font-weight:500;color:#8a8577"> {unit}</span></div>'
                f'<div style="font-size:13px;color:#8a8577;margin-top:4px">{label}</div></div>')

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>麦门周报 · 麦卡路里</title></head>
<body style="margin:0;background:#f6f4ef;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
<div style="max-width:640px;margin:0 auto;padding:24px 16px">
  <div style="background:{MCD_RED};border-radius:20px;padding:26px 24px;color:#fff;position:relative;overflow:hidden">
    <div style="position:absolute;right:-30px;top:-40px;width:150px;height:150px;border-radius:50%;background:{MCD_YELLOW};opacity:.9"></div>
    <div style="position:absolute;right:40px;top:-70px;width:150px;height:150px;border-radius:50%;background:{MCD_YELLOW};opacity:.55"></div>
    <div style="font-size:14px;opacity:.85">{week[0].month}月{week[0].day}日 – {week[-1].month}月{week[-1].day}日</div>
    <div style="font-size:32px;font-weight:900;margin-top:4px">麦门周报 🍟</div>
    <div style="font-size:14px;margin-top:10px;opacity:.92">{verdict}</div>
  </div>
  <div style="display:flex;gap:10px;margin-top:14px">
    {stat(int(total_kcal), "千卡", "本周总热量", MCD_RED)}
    {stat(active, f"/7 天", "有记录天数")}
    {stat(f"{total_amount:.0f}", "元", "本周吃麦当劳花费")}
  </div>
  <div style="background:#fff;border-radius:20px;padding:20px;margin-top:14px;box-shadow:0 2px 10px rgba(0,0,0,.05)">
    <div style="font-weight:800;font-size:16px;margin-bottom:8px">每日热量 <span style="font-weight:400;color:#8a8577;font-size:13px">目标 {int(target)} 千卡/餐</span></div>
    {bar_chart(days, target)}
  </div>
  <div style="background:#fff;border-radius:20px;padding:20px;margin-top:14px;box-shadow:0 2px 10px rgba(0,0,0,.05)">
    <div style="font-weight:800;font-size:16px;margin-bottom:8px">营养素结构</div>
    {donut(tp, tf, tc)}
  </div>
  <div style="background:#fff;border-radius:20px;padding:20px;margin-top:14px;box-shadow:0 2px 10px rgba(0,0,0,.05)">
    <div style="font-weight:800;font-size:16px;margin-bottom:4px">本周最爱</div>
    {top_html}
  </div>
  <div style="text-align:center;color:#b3ad9c;font-size:12px;margin:18px 0">麦卡路里 · 数据来自麦当劳 MCP 真实订单与营养库 · 仅供健康参考</div>
</div></body></html>"""


def main() -> None:
    base = os.path.expanduser("~/.workbuddy/skills-data/maikaluli")
    argv = sys.argv[1:]
    out = "weekly_report.html"
    if "-o" in argv:
        i = argv.index("-o")
        out = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    ledger = load_json(argv[0] if argv else os.path.join(base, "ledger.json"), {"entries": []})
    profile = load_json(argv[1] if len(argv) > 1 else os.path.join(base, "profile.json"), {})
    html = render(ledger, profile)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(out)


if __name__ == "__main__":
    main()
