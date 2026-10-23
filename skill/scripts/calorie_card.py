#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦卡路里 · 卡路里卡片生成器

把一单餐品渲染成「热量主角」的麦当劳风格 HTML 卡片：总热量大字、单件热量明细、
三大营养素占比条、对比目标的进度。商品图从 URL 下载内嵌 base64，自包含可分享。

用法:
    python calorie_card.py input.json [-o output.html]

输入 JSON:
{
  "title": "今日午餐",
  "target": 600,
  "items": [{"name": "汉堡包", "qty": 1, "kcal": 248, "price": 15.0,
             "protein": 13, "fat": 8, "carb": 29,
             "image": "https://menu-img.mcd.cn/.../MS_901000_320.png"}],
  "estimated": false
}

配色: 薯条红 #DA291C / 金拱黄 #FFC72C。
"""

import base64
import json
import sys
import urllib.request

MCD_RED = "#DA291C"
MCD_YELLOW = "#FFC72C"
MCD_DARK = "#27251F"


def fetch_b64(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return "data:image/png;base64," + base64.b64encode(r.read()).decode()
    except Exception:
        return ""


def macro_bar(p: float, f: float, c: float) -> str:
    total = (p + f + c) or 1
    segs = [("蛋白质", p, MCD_RED), ("脂肪", f, MCD_YELLOW), ("碳水", c, MCD_DARK)]
    bar = "".join(
        f'<div style="width:{v/total*100:.1f}%;background:{color};height:100%"></div>'
        for _, v, color in segs if v > 0)
    legend = "".join(
        f'<div style="flex:1;text-align:center"><div style="font-weight:800;font-size:17px;color:{color}">{v:.0f}g</div>'
        f'<div style="font-size:12px;color:#8a8577">{name}</div></div>'
        for name, v, color in segs)
    return (f'<div style="display:flex;height:10px;border-radius:999px;overflow:hidden;background:#f0ece1">{bar}</div>'
            f'<div style="display:flex;margin-top:10px">{legend}</div>')


def item_row(it: dict) -> str:
    img = fetch_b64(it["image"]) if it.get("image") else ""
    thumb = (f'<img src="{img}" style="width:64px;height:64px;object-fit:contain;flex:none">'
             if img else '<div style="width:64px;height:64px;flex:none"></div>')
    price = f'<div style="font-size:12px;color:#b3ad9c">¥{it["price"]:.1f} × {it.get("qty",1)}</div>' if it.get("price") else ""
    return f"""
    <div style="display:flex;align-items:center;gap:14px;padding:12px 0;border-bottom:1px dashed #eee">
      {thumb}
      <div style="flex:1">
        <div style="font-weight:700;font-size:15px;color:{MCD_DARK}">{it['name']}</div>
        {price}
      </div>
      <div style="text-align:right">
        <div style="font-weight:900;font-size:22px;color:{MCD_DARK}">{it['kcal']*it.get('qty',1):.0f}</div>
        <div style="font-size:11px;color:#8a8577">千卡</div>
      </div>
    </div>"""


def render(data: dict) -> str:
    items = data.get("items", [])
    total_kcal = sum(i.get("kcal", 0) * i.get("qty", 1) for i in items)
    tp = sum(i.get("protein", 0) * i.get("qty", 1) for i in items)
    tf = sum(i.get("fat", 0) * i.get("qty", 1) for i in items)
    tc = sum(i.get("carb", 0) * i.get("qty", 1) for i in items)
    target = data.get("target")
    est = "（含估算）" if data.get("estimated") else ""

    hero_sub, gauge = "", ""
    if target:
        pct = total_kcal / target * 100
        over = total_kcal > target
        color = MCD_RED if over else "#2e9e4f"
        word = f"超目标 {pct-100:.0f}%" if over else f"目标内，还剩 {target-total_kcal:.0f} 千卡额度"
        width = min(pct, 100)
        hero_sub = f'<div style="font-size:14px;opacity:.92;margin-top:4px">{word}{est}</div>'
        gauge = (f'<div style="background:rgba(255,255,255,.25);height:8px;border-radius:999px;margin-top:12px">'
                 f'<div style="width:{width:.0f}%;background:#fff;height:100%;border-radius:999px"></div></div>')

    items_html = "".join(item_row(i) for i in items)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>卡路里卡片 · 麦卡路里</title></head>
<body style="margin:0;background:#f6f4ef;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
<div style="max-width:460px;margin:0 auto;padding:28px 16px">
  <div style="background:{MCD_RED};border-radius:22px;padding:26px 24px;color:#fff;position:relative;overflow:hidden">
    <div style="position:absolute;right:-36px;top:-46px;width:160px;height:160px;border-radius:50%;background:{MCD_YELLOW};opacity:.9"></div>
    <div style="position:relative">
      <div style="font-size:14px;opacity:.85">{data.get('title','这一单')}</div>
      <div style="font-size:52px;font-weight:900;line-height:1.1">{total_kcal:.0f}<span style="font-size:18px;font-weight:600"> 千卡</span></div>
      {hero_sub}{gauge}
    </div>
  </div>
  <div style="background:#fff;border-radius:20px;padding:18px 22px;margin-top:14px;box-shadow:0 2px 10px rgba(0,0,0,.05)">
    {items_html}
  </div>
  <div style="background:#fff;border-radius:20px;padding:20px 22px;margin-top:14px;box-shadow:0 2px 10px rgba(0,0,0,.05)">
    <div style="font-weight:800;font-size:15px;margin-bottom:12px">三大营养素</div>
    {macro_bar(tp, tf, tc)}
  </div>
  <div style="text-align:center;color:#b3ad9c;font-size:12px;margin-top:16px">
    麦卡路里 · 营养数据来自麦当劳官方营养库{(' · ' + est) if est else ''} · 仅供参考</div>
</div></body></html>"""


def main() -> None:
    argv = sys.argv[1:]
    out = "calorie_card.html"
    if "-o" in argv:
        i = argv.index("-o")
        out = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        print("usage: calorie_card.py input.json [-o out.html]")
        sys.exit(1)
    with open(argv[0], encoding="utf-8") as f:
        data = json.load(f)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data))
    print(out)


if __name__ == "__main__":
    main()
