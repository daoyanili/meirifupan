# 数据存储说明

## 当前存储方式

项目现在使用 SQLite 存储市场数据，数据库文件为：

```text
data/market_review.db
```

旧的 JSON 文件仍保留在 `data/uplimit/`，只作为历史原始文件和迁移来源。新的抓取流程会直接写入数据库。

## 数据分层

| 层级 | 表 | 作用 |
|------|------|------|
| 原始层 | `raw_api_responses` | 保存接口原始返回，方便追溯和重算 |
| 基础层 | `trade_calendar`、`stocks`、`plates` | 保存交易日、股票、板块基础信息 |
| 事件层 | `limit_up_events`、`limit_up_plate_map` | 保存涨停事件和股票-板块关系 |
| 排名层 | `plate_hot_rank`、`plate_daily` | 保存热门板块和板块排名 |
| 扩展数据层 | `plate_trends`、`plate_reasons`、`lhb_daily`、`movement_alerts`、`market_index_daily`、`sentiment_daily`、`market_hot_daily`、`stock_kline_daily`、`stock_trends`、`stock_info_snapshots` | 保存后续复盘和看盘会用到的数据 |
| 分析层 | `daily_reviews` | 后续保存自动复盘结论 |
| 任务层 | `data_jobs` | 后续记录采集、分析、推送任务 |

## 为什么拆成多张表

接口返回的涨停数据是“板块里套股票”。同一只股票可能属于多个板块，如果直接累加会重复统计。

现在改成：

```text
limit_up_events       一只股票一天只保存一条涨停事件
limit_up_plate_map    一只股票一天可以关联多个板块
```

这样既能得到真实涨停数量，也能分析题材扩散情况。

## 已迁移数据

当前已从 `data/uplimit/uplimit_*.json` 迁移 13 个交易日：

```text
2026-05-12 ~ 2026-06-01
```

迁移后的主要数据量：

| 表 | 数量 |
|------|------:|
| `trade_calendar` | 13 |
| `stocks` | 729 |
| `plates` | 258 |
| `raw_api_responses` | 13 |
| `limit_up_events` | 1048 |
| `limit_up_plate_map` | 12432 |
| `plate_hot_rank` | 246 |
| `plate_daily` | 390 |

目前本地历史文件里只有涨停、热门板块、板块排名这几类真实数据。其他表已经建好，但还没有采集到对应数据，行数为 0。

可用 `python src/db_inventory.py` 查看所有表的行数。

## 数据获取方式

当前主数据源是 `quant.zizizaizai.com`，由 `src/api_client.py` 封装接口。

已经接入并落库：

| 数据 | 方法 | 入库表 |
|------|------|------|
| 交易日历 | `get_trade_days()` | `trade_calendar` |
| 涨停原因 | `get_uplimit_reason()` | `limit_up_events`、`limit_up_plate_map`、`stocks`、`plates` |
| 涨停热门板块 | `get_uplimit_hot()` | `plate_hot_rank` |
| 板块排名 | `get_plate_rank()` | `plate_daily` |

已建表但还未进入日常采集：

| 数据 | 方法 | 目标表 |
|------|------|------|
| 板块趋势 | `get_plate_trend()` | `plate_trends` |
| 板块热门原因 | `get_plate_reason()` | `plate_reasons` |
| 龙虎榜 | `get_lhb()` | `lhb_daily` |
| 盘中异动 | `get_alerts()` | `movement_alerts` |
| 大盘指数走势 | `get_index_trends()` | `market_index_daily` |
| 市场情绪 K 线 | `get_sentiment_kline()` | `sentiment_daily` |
| 市场热点 | `get_market_hot()` | `market_hot_daily` |
| 个股日 K | `get_stock_kline()` | `stock_kline_daily` |
| 个股分时 | `get_stock_trend()` | `stock_trends` |
| 个股资料 | `get_stock_info()` | `stock_info_snapshots` |

## 常用命令

迁移历史 JSON：

```bash
python src/migrate_json_to_db.py
```

抓取最近交易日并直接写入数据库：

```bash
python src/fetch_uplimit.py
```

查看数据库覆盖情况：

```bash
python src/db_inventory.py
```

运行测试：

```bash
python -m unittest tests/test_market_db.py -v
```
