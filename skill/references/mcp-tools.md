# 麦当劳 MCP（mcd-mcp）实测参考

> 本文档基于 2026-10-23 对生产环境的真实调用整理，优先于官方文档的 5 工具基线。

## 接入配置

WorkBuddy 配置文件：`~/.workbuddy/mcp.json`

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn/mcp-servers/mcd-mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MCP_TOKEN>"
      }
    }
  }
}
```

- Token 申请：open.mcd.cn/mcp → 手机号登录 → 控制台申请。
- 配置后在 WorkBuddy 连接器管理页点「信任」启用。
- 平台约束：协议版本 ≤ 2025-06-18；每 Token 600 次/分钟，超限 429。
- **安全**：Token 等同会员身份，禁止写入对外文件/仓库。

## 配餐链路调用时序（实测可行）

```
1. now-time-info                     # 拿服务器时间（判断券/活动有效性）
2. auto-bind-coupons                 # 一键领券（无参数）
3. delivery-query-addresses          # 外送地址列表 → addressId
4. delivery-query-stores             # 入参 {addressId, beType:2} → storeCode + beCode
5. query-meals                       # 入参 {storeCode, orderType:2, beType:2, beCode} → 全量菜单+实时价
6. list-nutrition-foods              # 无参数 → 160 个餐品营养库
7. query-store-coupons               # 入参同 query-meals → 该店可用券（含适用商品编码、有效期）
```

到店场景改用 `query-nearby-stores`（入参 `{beType:1, searchType, city?, keyword?}`），`orderType:1`。

## 关键工具实测笔记

| 工具 | 实测要点 |
|---|---|
| `query-meals` | 返回 `categories[]`（分类→餐品 code）+ `meals{}`（code→详情）。价格字段 `currentPrice`（字符串）。同一餐品可能在多分类重复，按 code 去重。注意剔除非食品（周边商品如徽章/帽子也混在菜单里，名称含"徽章/棒球帽/丝巾/毛绒"）。 |
| `list-nutrition-foods` | 返回文本格式：`[160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:` 后每行一个餐品。用 `energyKcal` 做热量。菜单名与营养库名可能略有差异（如菜单"麦辣鸡腿汉堡" vs 营养库"麦辣鸡腿堡"），需模糊匹配。 |
| `query-store-coupons` | 返回 `data[]`：`title`/`couponId`/`couponCode`/`tradeDateTime`（有效期）/`products[]`（适用商品编码+名称）。注意券可能当日到期，务必核对 `tradeDateTime`。 |
| `auto-bind-coupons` | 返回成功/失败计数与每张券的 couponId。领完后用 `query-my-coupons` 或 `query-store-coupons` 确认。 |
| `campaign-calendar` | 返回当月活动，分进行中/往期/未来，含活动图文。 |
| `delivery-query-stores` | 返回门店列表：`storeCode`/`beCode`/`storeName`/`businessStatus`（营业中）/`businessStartTime`/`businessEndTime`。选营业中的第一家或问用户。 |
| `calculate-price` | 入参 `{storeCode, orderType, beType, beCode, items[], ...}`，可验证方案真实应付（含配送费打包费），`items` 结构需按 query-meals 的商品编码组装，必要时用 `query-meal-detail` 查单品构成。 |
| `create-order` | 下单工具。**必须**先向用户复述订单明细并获明确同意才可调用。 |

## 其他可用工具（按需探索）

订单类：`order-list`、`query-order`、`cancel-order`、`mall-order-list`、`mall-order-detail`、`mall-create-order`、`mall-points-products`、`mall-product-detail`；营养/配餐辅助：`query-meal-detail`、`query-meal-assistance`（团餐）、`query-promotions`（团餐满减）；活动类：`draw-lottery`、`query-lottery-info`、`query-my-prizes`、`query-survey-coupon`；账户：`query-my-account`；团餐：`query-party-city`、`query-party-store`、`query-party-store-session`、`query-party-store-date`、`party-order-create`；地址：`delivery-create-address`。

## 错误处理

| 情况 | 处理 |
|---|---|
| 401/403 | Token 失效，引导重新申请 |
| 429 | 间隔 2 秒重试一次；仍失败告知限流稍后再试 |
| `businessStatus: false` | 门店休息中，换店或提示营业时间 |
| 营养库无此单品 | 常识估算并标「估」 |
