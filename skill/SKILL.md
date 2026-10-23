---
name: maikaluli
description: 麦卡路里——基于麦当劳 MCP 的热量管理配餐技能，带个人记忆与营养账本。当用户想按热量目标吃麦当劳（"午餐帮我配一顿 600 卡的"、"麦当劳怎么吃不超热量"、"巨无霸多少卡"、"帮我记住我不吃辣"）、要按口味禁忌/减脂增肌目标/预算配餐，或想同步麦当劳订单做饮食记录、生成"麦门周报"热量可视化卡片时使用。调用 mcd-mcp 拉取真实菜单、营养数据、优惠券与历史订单，用内置脚本配餐叠券、生成麦当劳风格周报，画像与账本存本地越用越懂你。
agent_created: true
---

# 麦卡路里 (MaiKaluli)

## Overview

按热量目标和口味偏好帮用户配麦当劳：真实菜单（`query-meals`）+ 真实营养数据（`list-nutrition-foods`）+ 真实优惠券（`query-store-coupons`），脚本求解「热量达标、口味合规、叠券最省」的方案。用户画像存本地记忆文件，越用越准。

## 记忆机制（核心差异）

**画像文件**：`~/.workbuddy/skills-data/maikaluli/profile.json`

```json
{
  "calorie_target": 600,
  "goal": "减脂",
  "dislike_tags": ["spicy"],
  "budget": 50,
  "store": {"storeCode": "...", "beCode": "...", "storeName": "..."},
  "people": 1,
  "updated_at": "2026-10-23"
}
```

- **读取**：每次配餐前必读。不存在 → 走「首次建档」。
- **更新**：用户说「改 1800 卡了」「不吃辣了」「以后就去 XX 店」等 → 立即改写对应字段并确认。只在用户明确表达偏好变化时更新。
- **隐私**：画像只存本机，绝不写入仓库、或任何对外文件。

## 前置检查

1. 确认 `mcd-mcp` 连接器可用。不可用 → 引导配置 `~/.workbuddy/mcp.json` 并「信任」启用（见 `references/mcp-tools.md`）。
2. 门店确定优先级：画像里的店 → `delivery-query-addresses` + `delivery-query-stores` 推导 → 问用户。确定后写入画像。

## 核心工作流

### 流程 0：首次建档（画像不存在时）

一次问完：每餐热量目标（默认 600）、目标（减脂/维持/增肌）、口味禁忌、预算、人数、堂食/外送。写入 profile.json 并复述确认。

### 流程 1：日常配餐（主场景）

触发：「午餐帮我配一顿」「今天吃麦当劳，别超热量」

1. 读画像；`auto-bind-coupons` 领券（省钱是标配动作）。
2. 并行拉数据：`query-meals`（门店真实菜单+价格）、`list-nutrition-foods`（营养库）、`query-store-coupons`（该店可用券）。链路细节见 `references/mcp-tools.md`。
3. 调用 `scripts/plan_meal.py`：传入菜单+营养+券+画像，得 Top 3 方案。营养库缺失的单品用常识估算并在输出标「估」。套餐类商品（四件套/双人餐等）营养库匹配不到时，可用 `query-meal-detail` 拆解成单品后分别查营养求和，比估算更准。
4. 输出每套方案：清单、总热量（vs 目标）、三大营养素简表、原价、用券、实付、省多少。推荐首选并说理由（如「蛋白质最高，适合减脂」）。用户选定方案后，可用 `scripts/calorie_card.py` 生成该方案的「卡路里卡片」（热量主角+营养素占比条，麦当劳红黄风），present 给用户。
5. 收尾提醒：以 App 实际结算与营养标示为准；不擅自下单。

### 流程 1.5：下单与订单卡片

触发：用户确认方案后说「下单/确认」，或事后说「把订单生成卡片」

1. 下单：`create-order` 前必须复述订单明细并获明确同意；建议先 `calculate-price` 验证真实应付（含运费打包费）再下单；支付由 MCP 返回的 payH5Url 或 App 完成。
2. 订单卡片：取 `create-order`/`query-order` 返回的商品明细与图片 URL，写入 order JSON（含每件 kcal），运行 `scripts/order_card.py` 生成麦当劳风格卡片，present 给用户。地址等隐私信息默认不写入卡片。

### 流程 2：查营养

触发：「巨无霸多少卡」「麦辣鸡翅热量」

直接调 `list-nutrition-foods`，返回热量+蛋白质/脂肪/碳水/钠，可顺带对比 1-2 个相近单品。

### 流程 3：记忆更新

触发：「记住我…」「我以后…」「我改成…」

改写 profile.json 对应字段，复述确认。若改了门店偏好，重新走门店查询更新 storeCode。

### 流程 4：活动/新品（顺带）

配餐时若 `campaign-calendar` 有进行中的活动特价品，加入候选并在方案里标注「活动款」。不主动长篇推活动。

### 流程 5：账本同步（差异化核心）

触发：「记一下我今天吃的」「同步我的订单」，或每次配餐/周报前自动执行。

1. 账本文件：`~/.workbuddy/skills-data/maikaluli/ledger.json`（entries 数组，格式见 `scripts/weekly_report.py` docstring）。
2. **自动同步**：调 `order-list` 拉真实订单 → 跳过已取消订单 → 逐商品精确匹配 `list-nutrition-foods` 营养（饮品注意温度杯型，如「热燕麦奶中杯」≠「燕麦奶」，拿不准用 `query-meal-detail` 查规格）→ 按下单日期写入账本，按 orderId 去重。
3. **手动记账**：用户口述吃了什么时，查营养库后追加 source=manual 的记录。
4. **配餐闭环**：流程 1 配餐前读本账本——本周累计已超目标时，主动收紧今日建议热量（如目标 -150），并说明原因。

### 流程 6：麦门周报

触发：「我的麦门周报」「这周吃得怎么样」

1. 先走流程 5 同步账本。
2. 运行 `scripts/weekly_report.py`（默认读账本+画像，`-o` 指定输出），生成麦当劳品牌风格 HTML 卡片（红 #DA291C / 黄 #FFC72C）。
3. 用 present_files 把卡片给用户，并配一句总结（超了几天、最爱吃什么、下周建议）。

## 硬性规则

- **不编造**：菜单、价格、营养、券只来自 MCP 返回；估算营养必须标「估」。
- **记忆诚实**：画像里没有的字段不要假装知道；不确定就问一次并记住。
- **Token 与隐私保密**：MCP Token、用户地址电话绝不写入任何对外文件或仓库。
- **下单需确认**：如调用下单工具，必须先复述订单明细并获明确同意。
- 429 限流：间隔 2 秒重试一次，仍失败告知用户稍后再试。

## Resources

- `references/mcp-tools.md`：mcd-mcp 工具实测文档——接入配置、配餐链路调用时序、关键入参（storeCode/beCode/beType/orderType）、错误处理。
- `scripts/plan_meal.py`：配餐优化器。`python scripts/plan_meal.py input.json`，输入输出格式见脚本 docstring。目标函数：热量贴近目标优先，同热量下叠券后实付最低。
- `scripts/weekly_report.py`：麦门周报卡片生成器。`python scripts/weekly_report.py [ledger.json] [profile.json] [-o out.html]`，默认读本机账本与画像，输出麦当劳风格自包含 HTML。
- `scripts/order_card.py`：订单卡片生成器。`python scripts/order_card.py order.json [-o out.html]`，商品图从 URL 下载内嵌 base64，输入格式见脚本 docstring。
- `scripts/calorie_card.py`：卡路里卡片生成器。`python scripts/calorie_card.py input.json [-o out.html]`，热量大字+目标进度+三大营养素占比条，输入格式见脚本 docstring。
