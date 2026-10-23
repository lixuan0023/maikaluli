#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦卡路里 · 订单卡片生成器

把麦当劳 MCP 返回的订单详情渲染成麦当劳风格的自包含 HTML 订单卡片。
商品图片从 MCP 返回的 URL 下载并内嵌为 base64，卡片可离线打开/截图分享。

用法:
    python order_card.py order.json [-o output.html]

输入 JSON（字段尽量与 mcd-mcp 的 create-order/query-order 返回对齐）:
{
  "orderId": "1030...",
  "storeName": "麦当劳深圳绒花路餐厅",
  "status": "待支付",
  "created": "2026-10-23 12:59",
  "items": [{"name": "汉堡包", "qty": 1, "price": 15.0,
             "image": "https://menu-img.mcd.cn/.../MS_901000_320.png",
             "kcal": 248}],
  "product_total": 45.0,
  "delivery_fee": 6.0,
  "packing_fee": 1.9,
  "total": 52.9,
  "address": "可选，收货地址（注意隐私，勿入仓库）"
}

kcal 可选：提供时卡片底部显示整单热量合计。
配色: 薯条红 #DA291C / 金拱黄 #FFC72C。
"""

import base64
import json
import os
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


def item_row(it: dict) -> str:
    img = fetch_b64(it["image"]) if it.get("image") else ""
    thumb = (f'<img src="{img}" style="width:56px;height:56px;object-fit:contain;flex:none">'
             if img else '<div style="width:56px;height:56px;flex:none"></div>')
    kcal = f'<div style="font-size:12px;color:#8a8577">{it["kcal"]:.0f} 千卡</div>' if it.get("kcal") else ""
    return f"""
    <div style="display:flex;align-items:center;gap:14px;padding:12px 0;border-bottom:1px dashed #eee">
      {thumb}
      <div style="flex:1">
        <div style="font-weight:700;font-size:15px;color:{MCD_DARK}">{it['name']}</div>
        {kcal}
      </div>
      <div style="color:#8a8577;font-size:14px">×{it.get('qty',1)}</div>
      <div style="font-weight:700;font-size:15px;width:64px;text-align:right">¥{it['price']:.1f}</div>
    </div>"""


def fee_row(label: str, val: float) -> str:
    return (f'<div style="display:flex;justify-content:space-between;padding:5px 0;font-size:14px;color:#555">'
            f'<span>{label}</span><span>¥{val:.1f}</span></div>')


def render(order: dict) -> str:
    items_html = "".join(item_row(i) for i in order.get("items", []))
    kcals = [i.get("kcal", 0) * i.get("qty", 1) for i in order.get("items", [])]
    total_kcal = sum(kcals) if any(kcals) else None
    kcal_line = (f'<div style="text-align:center;padding:10px;background:#fff8e1;border-radius:12px;'
                 f'font-size:14px;color:{MCD_DARK};margin-top:12px">🔥 本单约 <b style="color:{MCD_RED}">'
                 f'{total_kcal:.0f}</b> 千卡</div>') if total_kcal else ""
    addr = (f'<div style="font-size:13px;color:#8a8577;margin-top:6px">📍 {order["address"]}</div>'
            if order.get("address") else "")
    fees = fee_row("商品小计", order.get("product_total", 0))
    if order.get("delivery_fee"):
        fees += fee_row("外送费", order["delivery_fee"])
    if order.get("packing_fee"):
        fees += fee_row("打包费", order["packing_fee"])

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>麦门订单 · 麦卡路里</title></head>
<body style="margin:0;background:{MCD_RED};font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
<div style="max-width:460px;margin:0 auto;padding:32px 16px">
  <div style="text-align:center;margin-bottom:18px">
    <span style="display:inline-block;background:{MCD_YELLOW};color:{MCD_DARK};font-weight:900;
                 font-size:15px;padding:6px 18px;border-radius:999px">🍟 麦门订单</span>
  </div>
  <div style="background:#fff;border-radius:20px;padding:24px 22px;box-shadow:0 8px 24px rgba(0,0,0,.18)">
    <div style="display:flex;justify-content:space-between;align-items:baseline">
      <div style="font-weight:800;font-size:17px;color:{MCD_DARK}">{order.get('storeName','')}</div>
      <div style="font-size:13px;color:{MCD_RED};font-weight:700">{order.get('status','')}</div>
    </div>
    <div style="font-size:12px;color:#b3ad9c;margin-top:4px">订单号 {order.get('orderId','')} · {order.get('created','')}</div>
    {addr}
    <div style="margin-top:14px">{items_html}</div>
    <div style="margin-top:12px;padding-top:8px;border-top:2px solid {MCD_DARK}">
      {fees}
      <div style="display:flex;justify-content:space-between;padding-top:8px;margin-top:4px;
                  border-top:1px dashed #ddd;align-items:baseline">
        <span style="font-weight:800;font-size:16px">合计</span>
        <span style="font-weight:900;font-size:26px;color:{MCD_RED}">¥{order.get('total',0):.1f}</span>
      </div>
    </div>
    {kcal_line}
  </div>
  <div style="text-align:center;color:rgba(255,255,255,.75);font-size:12px;margin-top:16px">
    麦卡路里 · 订单数据来自麦当劳 MCP · 以 App 实际订单为准</div>
</div></body></html>"""


def main() -> None:
    argv = sys.argv[1:]
    out = "order_card.html"
    if "-o" in argv:
        i = argv.index("-o")
        out = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        print("usage: order_card.py order.json [-o out.html]")
        sys.exit(1)
    with open(argv[0], encoding="utf-8") as f:
        order = json.load(f)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(order))
    print(out)


if __name__ == "__main__":
    main()
