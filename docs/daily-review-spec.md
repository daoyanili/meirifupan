# 每日收盘复盘 -- 产品方案

## 一、产品定位与目标

### 解决什么问题

个人投资者收盘后面临三个痛点：

1. **信息分散** -- 涨停数据在东方财富，板块排名在同花顺，龙虎榜在交易所网站，情绪指标靠自己算。每天要翻 3-4 个平台才能拼出全貌。
2. **缺乏结构** -- 看完一堆数据后，不知道该总结什么、重点看什么。没有固定的复盘框架，每次复盘质量不稳定。
3. **无法积累** -- 今天的复盘结论明天就忘了，更别说和上周、上月的行情做对比。

### 给谁用

自己。一个每天花 30-60 分钟做 A 股短线复盘的个人投资者。

### 一句话定位

**收盘后跑一条命令，10 分钟内拿到结构化复盘报告，存入 Obsidian 形成可回溯的投研日志。**

### 成功标准

| 指标 | 目标 |
|------|------|
| 报告生成耗时 | < 30 秒（数据已入库的前提下） |
| 报告完整度 | 5 个核心模块全部有数据 |
| 日常可用性 | 每个交易日收盘后 15:30 前能跑完 |
| 历史可追溯 | 能对比近 5 个交易日的同类指标 |

---

## 二、用户故事

### US-01 大盘总览

> 作为一个短线交易者，我想要收盘后 30 秒内知道今天大盘涨跌、量能、市场风格，以便快速判断明天的操作方向。

**验收标准：**
- 显示上证指数、深证成指、创业板指的收盘价、涨跌幅、成交额
- 与前一交易日对比成交额，标注放量/缩量百分比
- 一句话总结市场风格（如"缩量震荡，题材轮动加快"）

**数据来源：** `market_index_daily` 表（需新增采集）

---

### US-02 涨停全景

> 作为一个打板选手，我想要快速看到今天的涨停数量、连板梯队、首板扩散情况，以便判断市场赚钱效应。

**验收标准：**
- 显示当日涨停总数、跌停总数、炸板数
- 按连板高度分层展示（最高板 -> 首板），每层显示股票数量和代表个股
- 标注与前一日对比的变化（涨停数增减、连板高度升降）

**数据来源：** `limit_up_events`、`sentiment_daily`（需新增采集跌停/炸板）

---

### US-03 板块轮动

> 作为一个关注主线的投资者，我想要知道今天哪些板块是主攻方向、哪些是退潮板块，以便调整持仓方向。

**验收标准：**
- 热门板块 Top 10，显示热度分和涨停股关联数
- 标注连续 N 天出现在热门榜单的板块（持续性）
- 标注今日新进热门板块 vs 昨日已有板块（新鲜度）

**数据来源：** `plate_hot_rank`、`limit_up_plate_map`、`plate_daily`

---

### US-04 情绪指标

> 作为一个需要判断市场温度的交易者，我想要一个量化的情绪评分，以便决定明天是进攻还是防守。

**验收标准：**
- 显示涨跌停比（涨停数 / 跌停数）
- 显示连板高度（最高几板）
- 显示首板数量（赚钱效应扩散度）
- 综合给出情绪评级：冰点 / 低迷 / 中性 / 亢奋 / 过热
- 与近 5 日情绪趋势对比

**数据来源：** `limit_up_events`、`sentiment_daily`（需新增采集）、`market_index_daily`

---

### US-05 高度股追踪

> 作为一个做龙头的交易者，我想要清晰看到市场高度股（连板最高、辨识度最高）的表现，以便判断市场空间。

**验收标准：**
- 列出当日连板最高的 5 只股票，显示连板数、涨停时间、所属板块、封单金额
- 标注哪些是"一字板"（买不到）vs "换手板"（可以参与）
- 标注哪些高度股今日断板

**数据来源：** `limit_up_events`（up_limit_keep_times, up_limit_type, fengdan_money）

---

### US-06 板块内部结构

> 作为一个做板块轮动的交易者，我想要看到每个热门板块内部有几只涨停、几只首板几只连板，以便判断板块所处阶段。

**验收标准：**
- 对 Top 5 热门板块，显示板块内涨停股列表
- 每个板块标注：涨停数、首板数、连板数、最早涨停时间
- 标注板块是否处于"启动期"（首板多）/"高潮期"（连板多）/"退潮期"（涨停数骤减）

**数据来源：** `limit_up_plate_map`、`limit_up_events`、`plate_hot_rank`

---

### US-07 Obsidian 归档

> 作为一个 Obsidian 用户，我想要复盘报告自动存入我的知识库，以便长期积累和回溯。

**验收标准：**
- 文件名：`YYYY-MM-DD-复盘.md`
- 存放路径：`{vault_path}/发家致富/复盘/`
- 包含 YAML frontmatter（日期、标签、情绪评级）
- 使用 Obsidian 兼容的 Markdown 语法（表格、callout）
- 可通过 Obsidian 搜索"复盘"或日期快速定位

---

## 三、功能设计

### 模块一：大盘复盘

**展示数据：**

| 字段 | 说明 | 数据来源 |
|------|------|----------|
| 上证指数收盘价 | 当日收盘点位 | `market_index_daily` |
| 上证涨跌幅 | 百分比 | `market_index_daily` |
| 深证成指收盘价 | 当日收盘点位 | `market_index_daily` |
| 深证涨跌幅 | 百分比 | `market_index_daily` |
| 创业板指收盘价 | 当日收盘点位 | `market_index_daily` |
| 创业板涨跌幅 | 百分比 | `market_index_daily` |
| 两市成交额 | 亿元 | `market_index_daily` |
| 前日成交额 | 亿元 | `market_index_daily`（前一日） |
| 量能变化 | 百分比，标注放量/缩量 | 计算得出 |
| 市场风格 | 一句话描述 | 规则生成 |

**交互方式：**
- 看板页面：顶部卡片区域，横向排列 3 个指数卡片 + 1 个量能卡片
- Markdown 报告：一级标题下的表格

**数据采集需求：** 需新增调用 `api_client.get_index_trends()` 并入库 `market_index_daily`

---

### 模块二：涨停全景

**展示数据：**

| 字段 | 说明 | 数据来源 |
|------|------|----------|
| 涨停总数 | 去重后涨停股数量 | `limit_up_events` COUNT(DISTINCT stock_code) |
| 跌停总数 | 当日跌停数量 | `sentiment_daily.limit_down_count`（需新增采集） |
| 炸板数 | 盘中涨停后打开的数量 | 需新增数据源 |
| 首板数量 | up_limit_desc 含"首板" | `limit_up_events` |
| 连板数量 | up_limit_desc 不含"首板" | `limit_up_events` |
| 最高板 | max(up_limit_keep_times) | `limit_up_events` |
| 涨停数 vs 前日 | 增减量 | 与 `limit_up_events` 前一日对比 |
| 连板高度 vs 前日 | 升降 | 与前一日最高板对比 |

**连板梯队展示：**

按 `up_limit_keep_times` 分组，从高到低排列。每组显示：
- 梯队名称（如"4连板"）
- 股票数量
- 代表个股（最多显示 5 只，按封单金额排序）
- 每只个股显示：股票名、涨停时间、是否一字板

**数据来源 SQL 逻辑：**

```sql
-- 涨停统计
SELECT
    COUNT(DISTINCT stock_code) AS total_limit_up,
    SUM(CASE WHEN up_limit_desc LIKE '%首板%' THEN 1 ELSE 0 END) AS first_board,
    SUM(CASE WHEN up_limit_desc NOT LIKE '%首板%' THEN 1 ELSE 0 END) AS multi_board,
    MAX(up_limit_keep_times) AS highest_board
FROM limit_up_events
WHERE trade_date = ?

-- 连板梯队
SELECT
    up_limit_keep_times AS board_count,
    COUNT(*) AS stock_count,
    GROUP_CONCAT(stock_name, ', ') AS stocks
FROM limit_up_events
WHERE trade_date = ? AND up_limit_keep_times >= 2
GROUP BY up_limit_keep_times
ORDER BY up_limit_keep_times DESC
```

---

### 模块三：板块轮动

**展示数据：**

| 字段 | 说明 | 数据来源 |
|------|------|----------|
| 板块排名 | Top 10 热门板块 | `plate_hot_rank` |
| 热度分 | 数值 | `plate_hot_rank.score` |
| 涨停关联数 | 该板块关联多少只涨停股 | `limit_up_plate_map` COUNT |
| 持续天数 | 连续几天出现在热门榜 | `plate_hot_rank` 多日对比 |
| 新鲜度 | 今日新进 vs 昨日已有 | 与前一日 `plate_hot_rank` 对比 |

**板块状态判断规则：**

| 状态 | 判断条件 | 含义 |
|------|----------|------|
| 启动期 | 首板占比 > 70%，热度分上升 | 板块刚开始发力，可以关注 |
| 高潮期 | 连板占比 > 40%，热度分高位 | 板块已经充分演绎，追高风险大 |
| 退潮期 | 涨停数较前日下降 > 30% | 板块开始分化，注意风险 |
| 新晋 | 昨日不在 Top 10，今日进入 | 新题材出现，重点研究 |

**数据来源 SQL 逻辑：**

```sql
-- 热门板块 + 涨停关联数
SELECT
    r.plate_code,
    r.plate_name,
    r.score,
    r.rank_no,
    COUNT(DISTINCT m.stock_code) AS limit_up_count
FROM plate_hot_rank r
LEFT JOIN limit_up_plate_map m
    ON r.trade_date = m.trade_date AND r.plate_code = m.plate_code
WHERE r.trade_date = ? AND r.source = 'uplimit_hot'
GROUP BY r.plate_code
ORDER BY r.rank_no
LIMIT 10

-- 板块持续性（近 5 日）
SELECT
    plate_code,
    plate_name,
    COUNT(*) AS days_in_hot,
    MIN(rank_no) AS best_rank
FROM plate_hot_rank
WHERE trade_date IN (?, ?, ?, ?, ?) AND source = 'uplimit_hot'
GROUP BY plate_code
HAVING days_in_hot >= 2
ORDER BY days_in_hot DESC, best_rank ASC
```

---

### 模块四：情绪指标

**情绪评分模型（v1 简单规则）：**

| 指标 | 权重 | 评分规则 |
|------|------|----------|
| 涨停数 | 30% | < 30: 0分, 30-60: 1分, 60-100: 2分, > 100: 3分 |
| 连板高度 | 25% | < 3板: 0分, 3板: 1分, 4板: 2分, >= 5板: 3分 |
| 首板数 | 20% | < 20: 0分, 20-50: 1分, 50-80: 2分, > 80: 3分 |
| 涨跌停比 | 15% | < 2: 0分, 2-5: 1分, 5-10: 2分, > 10: 3分 |
| 大盘涨跌 | 10% | 跌 > 1%: 0分, 平: 1分, 涨 < 1%: 2分, 涨 > 1%: 3分 |

**综合得分 = 加权平均，映射到情绪等级：**

| 得分区间 | 情绪等级 | 操作建议 |
|----------|----------|----------|
| 0 - 0.8 | 冰点 | 空仓等待，寻找错杀机会 |
| 0.8 - 1.5 | 低迷 | 轻仓试错，只做确定性高的 |
| 1.5 - 2.2 | 中性 | 正常仓位，跟随主线 |
| 2.2 - 2.7 | 亢奋 | 控制仓位，注意高位风险 |
| 2.7 - 3.0 | 过热 | 减仓，准备撤退 |

**数据来源：** `limit_up_events`（涨停数、首板数、连板高度）、`sentiment_daily`（跌停数，需新增采集）、`market_index_daily`（大盘涨跌，需新增采集）

---

### 模块五：高度股追踪

**展示数据：**

| 字段 | 说明 | 数据来源 |
|------|------|----------|
| 股票名称 | - | `limit_up_events.stock_name` |
| 股票代码 | - | `limit_up_events.stock_code` |
| 连板数 | up_limit_keep_times | `limit_up_events` |
| 涨停时间 | 越早越强 | `limit_up_events.up_limit_time` |
| 板型 | 一字板 / 换手板 | `limit_up_events.up_limit_type` |
| 封单金额 | 万元 | `limit_up_events.fengdan_money` |
| 封单率 | 百分比 | `limit_up_events.fengdan_rate` |
| 所属板块 | 主要板块 | `limit_up_plate_map` |
| 涨停原因 | - | `limit_up_events.reason` |

**筛选条件：** `up_limit_keep_times >= 2` 或 `fengdan_money` 排名前 10

**排序：** 按连板数降序，同连板按封单金额降序

---

### 模块六：板块内部结构（P1）

**展示数据：**

对 Top 5 热门板块，分别展示：

| 字段 | 说明 |
|------|------|
| 板块名称 | - |
| 涨停股数 | 板块内涨停数量 |
| 首板数 | 首板涨停数量 |
| 连板数 | 连板涨停数量 |
| 代表个股 | 最早涨停的 3 只 |
| 板块阶段 | 启动 / 高潮 / 退潮 |

**数据来源 SQL：**

```sql
SELECT
    p.plate_name,
    COUNT(DISTINCT e.stock_code) AS total,
    SUM(CASE WHEN e.up_limit_desc LIKE '%首板%' THEN 1 ELSE 0 END) AS first_board,
    SUM(CASE WHEN e.up_limit_desc NOT LIKE '%首板%' THEN 1 ELSE 0 END) AS multi_board
FROM limit_up_plate_map p
JOIN limit_up_events e
    ON p.trade_date = e.trade_date AND p.stock_code = e.stock_code
WHERE p.trade_date = ? AND p.plate_code = ?
GROUP BY p.plate_code
```

---

## 四、看板页面设计

### 页面布局（从上到下）

```
+---------------------------------------------------------------+
|  [日期选择器]  [生成报告]  [上一日] [下一日]                   |
+---------------------------------------------------------------+
|  [上证指数卡片] [深证成指卡片] [创业板指卡片] [量能卡片]        |
|  收盘价 涨跌幅   收盘价 涨跌幅   收盘价 涨跌幅   成交额 对比    |
+---------------------------------------------------------------+
|  [涨停数] [跌停数] [首板数] [连板数] [最高板] [情绪等级]        |
|   120      3       99      21      4连板     亢奋              |
+---------------------------------------------------------------+
|  涨停梯队 (左半)              |  热门板块 Top 10 (右半)         |
|  ┌─────────────────────┐     |  ┌──────────────────────┐     |
|  │ 4连板 (2)            │     |  │ 1. AI应用    13426   │     |
|  │  合锻智能 09:32      │     |  │ 2. 算力      8176   │     |
|  │  粤电力A  10:05      │     |  │ 3. 机器人    7143   │     |
|  │                      │     |  │ ...                  │     |
|  │ 3连板 (1)            │     |  │                      │     |
|  │  天地在线 10:12      │     |  │ [持续性标注] [新晋标注]│     |
|  │ ...                  │     |  └──────────────────────┘     |
|  └─────────────────────┘     |                                |
+---------------------------------------------------------------+
|  情绪趋势 (左半)              |  高度股明细 (右半)              |
|  ┌─────────────────────┐     |  ┌──────────────────────┐     |
|  │ 近5日情绪折线图       │     |  │ 股票 连板 时间 板型   │     |
|  │ 冰点-低迷-中性-亢奋  │     |  │ 合锻智能 4板 09:32 一字│    |
|  │                      │     |  │ 中京电子 4板 09:54 换手│    |
|  └─────────────────────┘     |  └──────────────────────┘     |
+---------------------------------------------------------------+
|  涨停股明细表格                                                    |
|  [板块筛选器] [搜索框]                                             |
|  股票 | 代码 | 板块 | 涨停时间 | 连板 | 封单 | 原因              |
|  ...                                                               |
+---------------------------------------------------------------+
```

### 交互细节

1. **日期选择器**：下拉框，显示数据库中所有可用交易日，默认最新一日
2. **生成报告**：按钮点击后调用后端 API，生成 Markdown 文件并下载
3. **上一日/下一日**：快速切换日期，无需重新打开页面
4. **板块筛选器**：涨停股表格上方，按板块过滤
5. **搜索框**：按股票名称或代码搜索
6. **情绪趋势图**：用 Canvas 绘制简单折线图，不需要引入图表库
7. **标注系统**：板块列表中用颜色标签标注"新晋"（绿色）、"持续"（蓝色）、"退潮"（灰色）

### 技术实现要点

- 前端继续使用 Vanilla JS，不引入框架
- 数据从 `data_server.py` 提供的 JSON API 获取，不再读 JSON 文件
- `data_server.py` 新增 `/api/review?date=YYYY-MM-DD` 接口，返回复盘所需全部数据
- 暗色主题保持现有风格

---

## 五、Markdown 报告模板

```markdown
---
title: "A股复盘 {date}"
date: {date}
tags: [复盘, A股, 短线]
emotion: {emotion_level}
limit_up_count: {limit_up_total}
---

# A股每日复盘 {date}

## 一、大盘总览

| 指数 | 收盘价 | 涨跌幅 | 成交额(亿) | 量能变化 |
|------|--------|--------|-----------|----------|
| 上证指数 | {sh_close} | {sh_pct}% | {sh_amount} | {sh_volume_change} |
| 深证成指 | {sz_close} | {sz_pct}% | {sz_amount} | {sz_volume_change} |
| 创业板指 | {cy_close} | {cy_pct}% | {cy_amount} | {cy_volume_change} |

> [!summary] 今日市场风格
> {market_style_summary}

## 二、涨停全景

| 指标 | 今日 | 昨日 | 变化 |
|------|------|------|------|
| 涨停数 | {limit_up} | {limit_up_prev} | {limit_up_diff} |
| 跌停数 | {limit_down} | {limit_down_prev} | {limit_down_diff} |
| 首板数 | {first_board} | {first_board_prev} | {first_board_diff} |
| 连板数 | {multi_board} | {multi_board_prev} | {multi_board_diff} |
| 最高板 | {highest_board}连板 | {highest_board_prev}连板 | {board_height_diff} |

### 连板梯队

{tier_details}

> 例：
> **4连板 (2只)**：合锻智能(09:32)、粤电力A(10:05)
> **3连板 (1只)**：天地在线(10:12)
> **2连板 (8只)**：春秋电子(09:30)、江苏国信(09:31)...

## 三、板块轮动

### 热门板块 Top 10

| 排名 | 板块 | 热度分 | 涨停关联数 | 持续天数 | 状态 |
|------|------|--------|-----------|----------|------|
| 1 | AI应用 | 13426 | 25 | 3天 | {status} |
| 2 | 算力 | 8176 | 33 | 5天 | {status} |
| ... | ... | ... | ... | ... | ... |

### 板块分析

{plate_analysis}

> [!tip] 板块观察
> - {plate_observation_1}
> - {plate_observation_2}

## 四、情绪指标

| 指标 | 数值 | 评分 |
|------|------|------|
| 涨停数 | {limit_up} | {score_limit_up}/3 |
| 连板高度 | {highest_board}板 | {score_board}/3 |
| 首板数 | {first_board} | {score_first}/3 |
| 涨跌停比 | {limit_ratio} | {score_ratio}/3 |
| 大盘涨跌 | {index_pct}% | {score_index}/3 |

**综合情绪：{emotion_level}（{emotion_score}/3）**

> [!warning] 操作建议
> {action_suggestion}

### 近5日情绪趋势

| 日期 | 涨停数 | 最高板 | 情绪等级 |
|------|--------|--------|----------|
| {d1} | {c1} | {b1} | {e1} |
| {d2} | {c2} | {b2} | {e2} |
| {d3} | {c3} | {b3} | {e3} |
| {d4} | {c4} | {b4} | {e4} |
| {d5} | {c5} | {b5} | {e5} |

## 五、高度股追踪

| 股票 | 代码 | 连板 | 涨停时间 | 板型 | 封单(万) | 板块 | 原因 |
|------|------|------|----------|------|----------|------|------|
| 合锻智能 | 603011 | 4板 | 09:32 | 一字 | 12000 | PCB设备 | 可控核聚变 |
| 中京电子 | 002579 | 4板 | 09:54 | 换手 | 8500 | 印制电路板 | 存储 |
| ... | ... | ... | ... | ... | ... | ... | ... |

## 六、涨停股明细

<details>
<summary>点击展开全部涨停股（{total}只）</summary>

| 股票 | 代码 | 板块 | 涨停时间 | 连板 | 封单(万) | 原因 |
|------|------|------|----------|------|----------|------|
| {stocks_table} |

</details>

## 七、明日关注

> [!info] 基于今日数据的观察
> 1. {observation_1}
> 2. {observation_2}
> 3. {observation_3}

---
*报告生成时间：{generated_at}*
*数据来源：第三方公开行情数据*
```

---

## 六、数据指标

### 功能质量指标

| 指标 | 定义 | 目标 |
|------|------|------|
| 报告生成成功率 | 成功生成报告 / 尝试次数 | > 99% |
| 模块数据完整度 | 有数据的模块数 / 总模块数 | 100%（核心5模块） |
| 数据准确率 | 与东方财富人工核对一致率 | > 95% |
| 生成耗时 | 从触发到文件写入完成 | < 30 秒 |

### 产品使用指标

| 指标 | 定义 | 目标 |
|------|------|------|
| 复盘覆盖率 | 实际复盘天数 / 交易天数 | > 90% |
| 报告阅读率 | 打开报告 / 生成报告 | 100%（自己用） |
| Obsidian 回溯率 | 回看历史报告的频率 | 每周至少 1 次 |

### 投资效果指标（长期）

| 指标 | 定义 | 目标 |
|------|------|------|
| 情绪判断准确率 | 次日大盘方向与情绪判断一致 | > 60% |
| 板块预判命中率 | 关注板块次日表现优于大盘 | > 55% |
| 复盘后操作胜率 | 基于复盘结论的操作盈利占比 | > 50% |

---

## 七、迭代规划

### Phase 1：基础复盘（第 1-2 周）-- 当前阶段

**目标：** 跑通"数据采集 -> 分析计算 -> 报告生成"全链路

| 任务 | 复杂度 | 依赖 | 说明 |
|------|--------|------|------|
| 新增 `market_index_daily` 采集 | M | api_client 已有方法 | 调用 `get_index_trends()` 入库 |
| 新增 `sentiment_daily` 采集 | M | api_client 已有方法 | 调用 `get_sentiment_kline()` 入库 |
| 编写复盘数据查询模块 `review_queries.py` | L | 数据库表结构 | 封装所有 SQL 查询 |
| 编写情绪评分计算模块 `emotion_scorer.py` | S | review_queries | 实现评分规则 |
| 编写 Markdown 报告生成器 `report_generator.py` | L | review_queries, emotion_scorer | 模板渲染 |
| 改造 `data_server.py` 新增复盘 API | M | review_queries | `/api/review?date=` |
| 改造前端看板 `index.html` | L | data_server API | 新增 5 个模块 |
| 定时调度脚本 `daily_review.py` | S | 全部 | 串联采集+分析+生成 |

**交付物：**
- `python src/daily_review.py --date 2026-06-03` 可生成完整报告
- 浏览器打开看板可查看当日复盘
- Obsidian 中有格式化的 .md 文件

---

### Phase 2：增强分析（第 3-4 周）

| 任务 | 复杂度 | 说明 |
|------|--------|------|
| 板块持续性分析 | M | 连续 N 天出现在热门榜的板块追踪 |
| 板块阶段判断 | M | 启动/高潮/退潮状态自动标注 |
| 历史对比增强 | M | 涨停数、情绪值近 5 日趋势图 |
| 板块内部结构模块 | L | Top 5 板块内部涨停分布 |
| 龙虎榜数据采集和展示 | L | 调用 `get_lhb()` 入库 `lhb_daily` |
| 涨停股次日表现追踪 | L | 需要采集涨停股次日 K 线 |

---

### Phase 3：智能分析（第 5-6 周）

| 任务 | 复杂度 | 说明 |
|------|--------|------|
| AI 摘要生成 | L | 用 LLM 对当日数据生成自然语言分析 |
| 板块轮动规律挖掘 | XL | 基于历史数据找板块轮动模式 |
| 情绪周期模型优化 | L | 用历史数据回测情绪评分准确率 |
| 异常检测 | M | 自动发现异常板块/个股（如突然爆发） |

---

### Phase 4：多端输出（第 7-8 周）

| 任务 | 复杂度 | 说明 |
|------|--------|------|
| 飞书/微信推送 | M | 每日报告自动推送到聊天工具 |
| Web 仪表盘升级 | L | 交互式图表，替代纯静态看板 |
| 自选股监控 | M | 基于 watchlist 的个性化复盘 |
| 持仓关联 | M | 复盘报告中显示持仓股表现 |

---

## 八、技术风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| API 接口变更 | 数据采集失败 | raw_api_responses 表保留原始数据，可重新解析 |
| 情绪评分不准 | 误导操作 | v1 用简单规则，后续用历史数据回测优化 |
| 指数数据缺失 | 大盘模块无数据 | 降级显示"数据暂缺"，不影响其他模块 |
| 前端渲染性能 | 大量涨停股时卡顿 | 分页加载，限制单页显示 200 条 |
| Obsidian 路径变化 | 报告写入失败 | 配置文件中维护 vault 路径，启动时校验 |

---

## 九、配置文件设计

```yaml
# config.yaml
database:
  path: "data/market_review.db"

obsidian:
  vault_path: "~/Documents/ObsidianVault"
  review_dir: "发家致富/复盘"

api:
  base_url: ""  # 数据接口地址，按需填写
  token: ""  # 可选

emotion:
  weights:
    limit_up_count: 0.30
    board_height: 0.25
    first_board_count: 0.20
    limit_ratio: 0.15
    index_change: 0.10
  thresholds:
    ice: 0.8
    low: 1.5
    neutral: 2.2
    high: 2.7

report:
  template: "templates/daily_review.md.j2"
  output_dir: "reports"
```
