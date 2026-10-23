#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦卡路里 · 配餐优化器

按热量目标 + 口味禁忌 + 预算，从真实菜单中配出套餐，并逐券评估取最省。
纯标准库，无第三方依赖。

用法:
    python plan_meal.py input.json
    cat input.json | python plan_meal.py

输入 JSON:
{
  "items": [                          // 门店真实菜单（必填）
    {"name": "麦辣鸡腿汉堡", "price": 25.5,
     "category": "burger",            // burger/combo/side/drink/dessert
     "tags": ["spicy"]}
  ],
  "nutrition": {                      // list-nutrition-foods 营养库（可空，缺则估算）
    "麦辣鸡腿堡": {"kcal": 485, "protein": 22, "fat": 24, "carb": 45}
  },
  "coupons": [                        // 门店可用券（可空）
    {"name": "满39减8", "type": "threshold", "threshold": 39, "discount": 8},
    {"name": "全单9折", "type": "percent", "rate": 0.9},
    {"name": "11.9吃堡", "type": "fixed_price", "item": "麦辣鸡腿汉堡", "price": 11.9},
    {"name": "中薯买送", "type": "bogo", "item": "中薯条"}
  ],
  "profile": {                        // 用户画像（必填核心字段）
    "calorie_target": 600,            // 每餐热量目标（千卡）
    "dislike_tags": ["spicy"],
    "budget": 50,
    "people": 1
  },
  "tolerance": 0.15,                  // 热量容差，默认 ±15%
  "max_items": 5,                     // 单方案最多件数，默认 5
  "shortlist": 18,                    // 参与枚举的候选数（按热量适配度截取），默认 18
  "top": 3
}

输出: plans 按「热量贴近目标 → 实付最低」排序，含热量、三大营养素、用券、实付、估算标记。
说明: 假设每单限用一张券；营养库缺失的单品按分类常识估算并标记 estimated。
"""

import json
import sys
from itertools import combinations

MAIN_CATEGORIES = {"burger", "combo", "main", "wrap", "rice", "breakfast"}
# 营养库缺失时的分类常识估算（千卡）
KCAL_FALLBACK = {"burger": 450, "combo": 800, "side": 250, "drink": 100, "dessert": 250}


def load_input() -> dict:
    raw = sys.stdin.read() if len(sys.argv) < 2 else open(sys.argv[1], encoding="utf-8").read()
    return json.loads(raw)


def norm(name: str) -> str:
    for ch in ("（", "）", "(", ")", " ", "大杯", "中杯", "-", "·"):
        name = name.replace(ch, "")
    return name


def find_nutrition(name: str, nutrition: dict, category: str = ""):
    """精确 → 归一化 → 互含子串 匹配营养库。套餐(combo)不做子串匹配，避免误配单品的营养值。"""
    if name in nutrition:
        return nutrition[name], False
    n = norm(name)
    for k, v in nutrition.items():
        if norm(k) == n:
            return v, False
    if category == "combo":
        return None, True
    for k, v in nutrition.items():
        nk = norm(k)
        if n and (n in nk or nk in n):
            return v, False
    return None, True


def coupon_effect(coupon: dict, basket: list):
    """返回节省金额，不适用返回 None。"""
    ctype = coupon.get("type")
    original = sum(i["price"] for i in basket)
    if ctype == "threshold":
        if original >= float(coupon["threshold"]):
            return float(coupon["discount"])
    elif ctype == "percent":
        return round(original * (1 - float(coupon["rate"])), 2)
    elif ctype == "fixed_price":
        for i in basket:
            if i["name"] == coupon.get("item") and i["price"] > float(coupon["price"]):
                return round(i["price"] - float(coupon["price"]), 2)
    elif ctype == "bogo":
        for i in basket:
            if i["name"] == coupon.get("item"):
                return i["price"]
    return None


def best_price(basket: list, coupons: list):
    original = sum(i["price"] for i in basket)
    final, cname = original, None
    for c in coupons:
        saved = coupon_effect(c, basket)
        if saved is not None and original - saved < final:
            final, cname = round(original - saved, 2), c["name"]
    return original, final, cname


def main() -> None:
    cfg = load_input()
    items = cfg.get("items", [])
    nutrition = cfg.get("nutrition", {})
    coupons = cfg.get("coupons", [])
    profile = cfg.get("profile", {})
    target = float(profile.get("calorie_target", 600))
    people = int(profile.get("people", 1))
    budget = profile.get("budget")
    dislike = set(profile.get("dislike_tags", []))
    tol = float(cfg.get("tolerance", 0.15))
    max_items = int(cfg.get("max_items", 5))
    shortlist = int(cfg.get("shortlist", 18))
    top = int(cfg.get("top", 3))
    goal_kcal = target * max(people, 1)

    # 过滤口味禁忌，挂营养数据
    pool = []
    for i in items:
        if dislike & set(i.get("tags", [])):
            continue
        item = dict(i)
        # 名称含套餐/件套/分享餐字样的按 combo 处理：营养库只含单品，子串匹配会漏算配餐
        eff_cat = i.get("category", "")
        if any(k in i["name"] for k in ("套餐", "件套", "分享餐", "拼", "桶")):
            eff_cat = "combo"
        nut, estimated = find_nutrition(i["name"], nutrition, eff_cat)
        if nut:
            item["kcal"] = float(nut.get("kcal", 0))
            item["protein"] = float(nut.get("protein", 0))
            item["fat"] = float(nut.get("fat", 0))
            item["carb"] = float(nut.get("carbohydrate", nut.get("carb", 0)))
        else:
            item["kcal"] = float(KCAL_FALLBACK.get(eff_cat, 250))
            item["protein"] = item["fat"] = item["carb"] = 0.0
        item["estimated"] = estimated
        pool.append(item)
    if not pool:
        print(json.dumps({"error": "过滤后无候选商品"}, ensure_ascii=False))
        sys.exit(1)

    # 候选截取：主食按「热量贴近目标 60%」排序，其余按「贴近目标 30%」排序
    mains = [i for i in pool if i.get("category") in MAIN_CATEGORIES]
    others = [i for i in pool if i.get("category") not in MAIN_CATEGORIES]
    mains.sort(key=lambda i: abs(i["kcal"] - goal_kcal * 0.6))
    others.sort(key=lambda i: abs(i["kcal"] - goal_kcal * 0.3))
    pool = (mains[:shortlist] + others[:shortlist])[: shortlist * 2]

    plans = []
    for size in range(1, min(max_items, len(pool)) + 1):
        for combo in combinations(pool, size):
            if sum(1 for i in combo if i.get("category") in MAIN_CATEGORIES) < people:
                continue
            kcal = sum(i["kcal"] for i in combo)
            if abs(kcal - goal_kcal) > tol * goal_kcal:
                continue
            original, final, cname = best_price(combo, coupons)
            if budget is not None and final > float(budget):
                continue
            plans.append({
                "items": [{"name": i["name"], "kcal": round(i["kcal"]),
                           "price": i["price"], "estimated": i["estimated"]} for i in combo],
                "total_kcal": round(kcal),
                "kcal_vs_target": round(kcal - goal_kcal),
                "protein_g": round(sum(i["protein"] for i in combo), 1),
                "fat_g": round(sum(i["fat"] for i in combo), 1),
                "carb_g": round(sum(i["carb"] for i in combo), 1),
                "original_total": round(original, 2),
                "coupon": cname or "无",
                "final_total": final,
                "saved": round(original - final, 2),
                "has_estimate": any(i["estimated"] for i in combo),
            })

    # 热量贴近目标优先，同偏差下实付最低
    plans.sort(key=lambda p: (abs(p["kcal_vs_target"]), p["final_total"]))
    seen, result = set(), []
    for p in plans:
        key = tuple(sorted(i["name"] for i in p["items"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
        if len(result) >= top:
            break

    print(json.dumps({
        "calorie_target": goal_kcal,
        "tolerance": f"±{int(tol * 100)}%",
        "budget": budget,
        "note": "假设每单限用一张券；estimated=true 的单品热量为分类常识估算；以麦当劳 App 实际为准",
        "plans": result,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
