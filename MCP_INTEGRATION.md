# MCP 集成说明（MCP_INTEGRATION）

本作品通过**麦当劳官方 MCP Server**获取真实的菜单、营养与优惠券数据，全程在 WorkBuddy 中调用。

## 接入方式

- MCP Server：`https://mcp.mcd.cn/mcp-servers/mcd-mcp`（Streamable HTTP）
- Token：在 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 手机号登录后于控制台申请
- WorkBuddy 配置（`~/.workbuddy/mcp.json`）：

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

配置后在 WorkBuddy 连接器管理页的自定义连接器入口点「信任」启用。

> 仓库中不含任何真实 Token 与用户隐私数据。`<YOUR_MCP_TOKEN>` 请替换为你自己的。

## 核心调用链路（已实测验证）

```
now-time-info                # 服务器时间
auto-bind-coupons            # 一键领券
delivery-query-addresses     # 外送地址 → addressId
delivery-query-stores        # {addressId, beType:2} → storeCode, beCode
query-meals                  # {storeCode, orderType:2, beType:2, beCode} → 实时菜单+价格
list-nutrition-foods         # 无参数 → 158 个餐品营养库（热量/蛋白质/脂肪/碳水/钠）
query-store-coupons          # 该店可用券（含适用商品编码、有效期）
        ↓
scripts/plan_meal.py         # 本地求解：热量达标 + 口味过滤 + 叠券最省
```

## 使用的 MCP 工具

| 工具 | 用途 |
|---|---|
| `query-meals` | 门店实时菜单与价格 |
| `list-nutrition-foods` | 餐品营养数据（热量管理核心） |
| `query-store-coupons` | 当前门店可用券 |
| `auto-bind-coupons` / `query-my-coupons` | 一键领券 / 我的卡包 |
| `delivery-query-addresses` / `delivery-query-stores` / `query-nearby-stores` | 门店定位（外送/到店） |
| `campaign-calendar` | 当月活动（活动款进入候选） |
| `now-time-info` | 服务器时间，判断券与活动有效性 |

更多工具（下单 `create-order`、算价 `calculate-price`、餐品构成 `query-meal-detail` 等 35 个）的实测笔记见 `skill/references/mcp-tools.md`。下单类工具设计上要求用户明确确认后才调用。

## 平台约束的处理

- 协议版本 ≤ 2025-06-18：WorkBuddy 满足。
- 600 次/分钟限流：查询类调用并行合并，计算全部下沉到本地脚本；遇 429 间隔 2 秒重试一次。
