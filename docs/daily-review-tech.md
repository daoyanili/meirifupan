现在我对整个代码库有了全面的了解。让我输出完整的技术方案。

---

# A股每日收盘复盘系统 -- 技术方案

## 一、总体架构

```
收盘后定时触发
       |
       v
+------------------+
|  fetch_daily.py  |  数据采集层
|  (爬取 + 清洗)   |
+--------+---------+
         |
         v
+------------------+
|   market_review.db |  数据存储层 (SQLite)
+--------+---------+
         |
    +----+----+
    |         |
    v         v
+-------+ +--------+
| data  | | report |
|server | | gen    |  服务层
|.py    | | .py    |
+---+---+ +---+----+
    |         |
    v         v
+-------+ +--------+
|index  | |.md     |
|.html  | |文件    |  展示层
+-------+ +--------+
```

## 二、数据采集层

### 2.1 需要采集的数据清单

根据已有空表和 api_client 方法，每日收盘需要采集以下数据：

| 序号 | 数据类型 | API 方法 | 目标表 | 更新策略 |
|------|----------|----------|--------|----------|
| 1 | 大盘指数 | `get_index_trends()` | `market_index_daily` | 增量（当日） |
| 2 | 涨停原因 | `get_uplimit_reason(date)` | `limit_up_events` + `limit_up_plate_map` | 全量覆盖当日 |
| 3 | 涨停梯队 | `get_uplimit_hot(date)` | `plate_hot_rank` | 全量覆盖当日 |
| 4 | 板块排名 | `get_plate_rank(date)` | `plate_daily` | 全量覆盖当日 |
| 5 | 龙虎榜 | `get_lhb(date)` | `lhb_daily` | 全量覆盖当日 |
| 6 | 盘中异动 | `get_alerts(date)` | `movement_alerts` | 全量覆盖当日 |
| 7 | 情绪K线 | `get_sentiment_kline(date)` | `sentiment_daily` | 全量覆盖当日 |
| 8 | 市场热点 | `get_market_hot(date)` | `market_hot_daily` | 全量覆盖当日 |
| 9 | 板块趋势(热门) | `get_plate_trend(code, start, end)` | `plate_trends` | 增量（追加） |
| 10 | 板块原因 | `get_plate_reason(code)` | `plate_reasons` | 按需更新 |

**不需要每日采集的**：
- `stock_kline_daily` -- 个股日K，量太大，按需（关注的个股才爬）
- `stock_trends` -- 个股分时，盘中实时数据，复盘不需要
- `stock_info_snapshots` -- 个股资料，低频变化，按需更新

### 2.2 api_client.py 新增方法

现有 API 方法已经覆盖了大部分需求，只需补充几个辅助方法。

```python
# api_client.py 新增方法

def get_index_daily(self, index_code: str, start_date: str, end_date: str) -> dict:
    """获取指数日K数据（上证/深证/创业板等）"""
    data = self._get(
        f"market/index/kline?index_code={index_code}"
        f"&day_start={start_date}&day_end={end_date}"
    )
    return data

def get_market_summary(self, date: str) -> dict:
    """获取市场概览（涨跌家数、成交额等）"""
    data = self._get(f"v3/api/market/summary?date1={date}")
    return data
```

### 2.3 fetch_daily.py 设计

```python
"""每日收盘数据采集脚本"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api_client import QuantAPI
from db import MarketDB

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fetch_daily")


class DailyFetcher:
    """每日数据采集器"""

    def __init__(self, api: QuantAPI, db: MarketDB):
        self.api = api
        self.db = db
        self.errors: list[str] = []

    def run(self, trade_date: str) -> dict:
        """执行完整的每日数据采集流程"""
        log.info(f"开始采集 {trade_date} 的数据")
        self.db.record_job("fetch_daily", trade_date, "running")

        results = {}
        steps = [
            ("大盘指数", self._fetch_index),
            ("涨停数据", self._fetch_uplimit),
            ("龙虎榜", self._fetch_lhb),
            ("盘中异动", self._fetch_alerts),
            ("情绪K线", self._fetch_sentiment),
            ("市场热点", self._fetch_market_hot),
            ("热门板块趋势", self._fetch_plate_trends),
        ]

        for name, func in steps:
            try:
                log.info(f"  采集: {name}")
                result = func(trade_date)
                results[name] = result
                log.info(f"  完成: {name}")
            except Exception as e:
                error_msg = f"{name} 采集失败: {e}"
                log.error(f"  {error_msg}")
                self.errors.append(error_msg)

            # 请求间隔，避免被限流
            time.sleep(0.5)

        # 记录任务状态
        status = "success" if not self.errors else "partial"
        message = "; ".join(self.errors) if self.errors else None
        self.db.record_job("fetch_daily", trade_date, status, message)
        self.db.conn.commit()

        log.info(f"采集完成: {len(results)}/{len(steps)} 成功")
        return results

    def _fetch_index(self, trade_date: str) -> dict:
        """采集大盘指数数据"""
        data = self.api.get_index_trends()
        if not data or data.get("code") != 20000:
            raise ValueError(f"API 返回异常: {data}")

        index_data = data.get("data", {})
        count = 0
        for index_code, items in index_data.items():
            for item in items:
                if item.get("date") == trade_date:
                    self.db.upsert_market_index(trade_date, index_code, item)
                    count += 1
        return {"index_count": count}

    def _fetch_uplimit(self, trade_date: str) -> dict:
        """采集涨停数据（复用 fetch_uplimit.py 逻辑）"""
        # 涨停原因
        reason_data = self.api.get_uplimit_reason(trade_date, page_size=200)
        plates = []
        if reason_data.get("code") == 20000:
            plates = reason_data.get("data", [])

        # 涨停梯队
        hot_data = self.api.get_uplimit_hot(trade_date, limit=20)
        hot_plates = []
        if hot_data.get("code") == 20000:
            hot_plates = hot_data.get("data", {}).get("plate", [])

        # 板块排名
        rank_data = self.api.get_plate_rank(trade_date, limit=30)
        plate_ranks = []
        if rank_data.get("code") == 20000:
            plate_ranks = rank_data.get("data", [])

        day_data = {
            "date": trade_date,
            "uplimit_reason": plates,
            "uplimit_hot": hot_plates,
            "plate_rank": plate_ranks,
        }
        self.db.import_uplimit_day(day_data, raw_source="api")

        total_stocks = sum(len(p.get("stocks", [])) for p in plates)
        return {"plates": len(plates), "stocks": total_stocks}

    def _fetch_lhb(self, trade_date: str) -> dict:
        """采集龙虎榜数据"""
        data = self.api.get_lhb(trade_date)
        if not data or data.get("code") != 20000:
            raise ValueError(f"API 返回异常")

        items = data.get("data", [])
        count = 0
        for item in items:
            self.db.upsert_lhb(trade_date, item)
            count += 1
        return {"count": count}

    def _fetch_alerts(self, trade_date: str) -> dict:
        """采集盘中异动"""
        data = self.api.get_alerts(trade_date, limit=200)
        if not data or data.get("code") != 20000:
            raise ValueError(f"API 返回异常")

        items = data.get("data", [])
        count = 0
        for item in items:
            self.db.upsert_movement_alert(trade_date, item)
            count += 1
        return {"count": count}

    def _fetch_sentiment(self, trade_date: str) -> dict:
        """采集情绪K线"""
        data = self.api.get_sentiment_kline(trade_date, period=0)
        if not data or data.get("code") != 20000:
            raise ValueError(f"API 返回异常")

        self.db.upsert_sentiment(trade_date, data.get("data", {}))
        return {"ok": True}

    def _fetch_market_hot(self, trade_date: str) -> dict:
        """采集市场热点"""
        data = self.api.get_market_hot(trade_date)
        if not data or data.get("code") != 20000:
            raise ValueError(f"API 返回异常")

        items = data.get("data", [])
        count = 0
        for item in items:
            self.db.upsert_market_hot(trade_date, item)
            count += 1
        return {"count": count}

    def _fetch_plate_trends(self, trade_date: str) -> dict:
        """采集当日热门板块的趋势数据"""
        # 从 plate_hot_rank 取当日 Top 10 板块
        hot_plates = self.db.get_hot_plates(trade_date, limit=10)
        if not hot_plates:
            return {"skipped": True, "reason": "no hot plates"}

        end_date = trade_date
        start_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")

        count = 0
        for plate in hot_plates:
            try:
                trend_data = self.api.get_plate_trend(
                    plate["plate_code"], start_date, end_date
                )
                if trend_data and trend_data.get("code") == 20000:
                    self.db.upsert_plate_trends(plate["plate_code"], trend_data.get("data", []))
                    count += 1
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"  板块趋势采集失败 {plate['plate_name']}: {e}")

        return {"plates": count}
```

### 2.4 数据更新策略总结

```
全量覆盖当日（每天重新采集，INSERT OR REPLACE）:
  - limit_up_events (按 trade_date + stock_code 去重)
  - limit_up_plate_map
  - plate_hot_rank
  - plate_daily
  - lhb_daily
  - movement_alerts
  - sentiment_daily
  - market_hot_daily
  - market_index_daily

增量追加:
  - plate_trends (按 plate_code + trade_date 去重)
  - plate_reasons (按 plate_code 去重)
  - raw_api_responses (只追加)
  - trade_calendar (只追加)

不自动采集（按需手动触发）:
  - stock_kline_daily
  - stock_trends
  - stock_info_snapshots
```

## 三、数据存储层

### 3.1 db.py 需要新增的方法

以下方法需要添加到 `MarketDB` 类中，用于写入当前空表的数据。

```python
# db.py 新增方法

def upsert_market_index(self, trade_date: str, index_code: str, data: dict) -> None:
    """写入大盘指数数据"""
    self.conn.execute(
        """
        INSERT INTO market_index_daily(trade_date, index_code, index_name, close_price, change_pct, amount, raw_payload)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trade_date, index_code) DO UPDATE SET
            index_name = excluded.index_name,
            close_price = excluded.close_price,
            change_pct = excluded.change_pct,
            amount = excluded.amount,
            raw_payload = excluded.raw_payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            trade_date,
            index_code,
            data.get("name") or data.get("index_name"),
            data.get("close") or data.get("close_price"),
            data.get("change_pct") or data.get("pct_chg"),
            data.get("amount"),
            json.dumps(data, ensure_ascii=False),
        ),
    )

def upsert_lhb(self, trade_date: str, item: dict) -> None:
    """写入龙虎榜数据"""
    stock_code = str(item.get("stock_code") or item.get("code") or "")
    if not stock_code:
        return
    self._upsert_stock(stock_code, item.get("stock_name"))
    reason = item.get("reason") or item.get("detail") or ""
    self.conn.execute(
        """
        INSERT INTO lhb_daily(trade_date, stock_code, stock_name, reason, buy_amount, sell_amount, net_buy_amount, raw_payload)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trade_date, stock_code, reason) DO UPDATE SET
            stock_name = excluded.stock_name,
            buy_amount = excluded.buy_amount,
            sell_amount = excluded.sell_amount,
            net_buy_amount = excluded.net_buy_amount,
            raw_payload = excluded.raw_payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            trade_date,
            stock_code,
            item.get("stock_name"),
            reason,
            item.get("buy_amount"),
            item.get("sell_amount"),
            item.get("net_buy_amount"),
            json.dumps(item, ensure_ascii=False),
        ),
    )

def upsert_movement_alert(self, trade_date: str, item: dict) -> None:
    """写入盘中异动数据"""
    import hashlib
    stock_code = str(item.get("stock_code") or item.get("code") or "")
    alert_time = item.get("time") or item.get("alert_time") or ""
    alert_text = item.get("text") or item.get("alert_text") or ""
    raw_hash = hashlib.md5(f"{trade_date}:{alert_time}:{stock_code}:{alert_text}".encode()).hexdigest()[:16]

    self.conn.execute(
        """
        INSERT INTO movement_alerts(trade_date, alert_time, stock_code, stock_name, alert_type, alert_text, price, change_pct, raw_hash, raw_payload)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trade_date, alert_time, stock_code, raw_hash) DO UPDATE SET
            stock_name = excluded.stock_name,
            alert_type = excluded.alert_type,
            alert_text = excluded.alert_text,
            price = excluded.price,
            change_pct = excluded.change_pct,
            raw_payload = excluded.raw_payload
        """,
        (
            trade_date,
            alert_time,
            stock_code,
            item.get("stock_name"),
            item.get("type") or item.get("alert_type"),
            alert_text,
            item.get("price"),
            item.get("change_pct"),
            raw_hash,
            json.dumps(item, ensure_ascii=False),
        ),
    )

def upsert_sentiment(self, trade_date: str, data: dict) -> None:
    """写入情绪K线数据"""
    self.conn.execute(
        """
        INSERT INTO sentiment_daily(trade_date, period, limit_up_count, limit_down_count, highest_board, raw_payload)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(trade_date, period) DO UPDATE SET
            limit_up_count = excluded.limit_up_count,
            limit_down_count = excluded.limit_down_count,
            highest_board = excluded.highest_board,
            raw_payload = excluded.raw_payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            trade_date,
            0,
            data.get("limit_up_count"),
            data.get("limit_down_count"),
            data.get("highest_board"),
            json.dumps(data, ensure_ascii=False),
        ),
    )

def upsert_market_hot(self, trade_date: str, item: dict) -> None:
    """写入市场热点数据"""
    item_key = str(item.get("key") or item.get("id") or item.get("name", ""))
    self.conn.execute(
        """
        INSERT INTO market_hot_daily(trade_date, item_key, item_name, score, rank_no, raw_payload)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(trade_date, item_key) DO UPDATE SET
            item_name = excluded.item_name,
            score = excluded.score,
            rank_no = excluded.rank_no,
            raw_payload = excluded.raw_payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            trade_date,
            item_key,
            item.get("name") or item.get("item_name"),
            item.get("score"),
            item.get("rank") or item.get("rank_no"),
            json.dumps(item, ensure_ascii=False),
        ),
    )

def upsert_plate_trends(self, plate_code: str, items: list[dict]) -> None:
    """写入板块趋势数据"""
    for item in items:
        trade_date = item.get("date") or item.get("trade_date")
        if not trade_date:
            continue
        self.conn.execute(
            """
            INSERT INTO plate_trends(plate_code, trade_date, plate_name, open_price, high_price, low_price, close_price, change_pct, amount, raw_payload)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plate_code, trade_date) DO UPDATE SET
                plate_name = excluded.plate_name,
                open_price = excluded.open_price,
                high_price = excluded.high_price,
                low_price = excluded.low_price,
                close_price = excluded.close_price,
                change_pct = excluded.change_pct,
                amount = excluded.amount,
                raw_payload = excluded.raw_payload,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                plate_code,
                trade_date,
                item.get("plate_name") or item.get("name"),
                item.get("open"),
                item.get("high"),
                item.get("low"),
                item.get("close"),
                item.get("change_pct") or item.get("pct_chg"),
                item.get("amount"),
                json.dumps(item, ensure_ascii=False),
            ),
        )

def get_hot_plates(self, trade_date: str, limit: int = 10) -> list[dict]:
    """获取当日热门板块列表"""
    rows = self.conn.execute(
        """
        SELECT plate_code, plate_name, score
        FROM plate_hot_rank
        WHERE trade_date = ? AND source = 'uplimit_hot'
        ORDER BY rank_no
        LIMIT ?
        """,
        (trade_date, limit),
    ).fetchall()
    return [dict(r) for r in rows]

def record_job(self, job_name: str, trade_date: str, status: str, message: str = None) -> None:
    """记录数据采集任务状态"""
    self.conn.execute(
        """
        INSERT INTO data_jobs(job_name, trade_date, status, message)
        VALUES(?, ?, ?, ?)
        """,
        (job_name, trade_date, status, message),
    )
```

### 3.2 daily_reviews 表结构补充

`daily_reviews` 表已在 db.py 中定义，用于存储自动复盘结论。字段设计：

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_date | TEXT PK | 交易日 |
| limit_up_stock_count | INTEGER | 涨停股数 |
| limit_up_plate_count | INTEGER | 涨停板块数 |
| first_board_count | INTEGER | 首板数 |
| multi_board_count | INTEGER | 连板数 |
| highest_board | INTEGER | 最高板数 |
| strongest_plates | TEXT (JSON) | 最强板块列表 |
| core_stocks | TEXT (JSON) | 核心股票列表 |
| summary | TEXT | Markdown 格式摘要 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

这个表由 `generate_review.py` 写入，不需要修改 DDL。

## 四、数据服务层

### 4.1 data_server.py 重构

将当前的单路由 HTML 服务重构为 RESTful JSON API 服务。

```python
"""本地数据 API 服务"""

from __future__ import annotations

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"


class MarketDBReader:
    """只读数据库查询层"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _query(self, sql: str, params=()) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def _query_one(self, sql: str, params=()) -> dict | None:
        conn = self._conn()
        try:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ========== 日期相关 ==========

    def get_trade_dates(self, limit: int = 20) -> list[str]:
        """获取有数据的交易日列表"""
        rows = self._query(
            """
            SELECT DISTINCT trade_date FROM limit_up_events
            ORDER BY trade_date DESC LIMIT ?
            """,
            (limit,),
        )
        return [r["trade_date"] for r in rows]

    # ========== 复盘概览 ==========

    def get_review_overview(self, trade_date: str) -> dict:
        """获取某日复盘概览数据"""
        conn = self._conn()
        try:
            overview = {}

            # 涨停统计
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_stocks,
                    COUNT(DISTINCT lpm.plate_code) as total_plates,
                    SUM(CASE WHEN COALESCE(le.up_limit_desc, '') LIKE '%首板%' OR le.up_limit_desc IS NULL THEN 1 ELSE 0 END) as first_board,
                    SUM(CASE WHEN le.up_limit_desc IS NOT NULL AND le.up_limit_desc NOT LIKE '%首板%' THEN 1 ELSE 0 END) as multi_board,
                    MAX(le.up_limit_keep_times) as highest_board
                FROM limit_up_events le
                LEFT JOIN limit_up_plate_map lpm ON le.trade_date = lpm.trade_date AND le.stock_code = lpm.stock_code
                WHERE le.trade_date = ?
                """,
                (trade_date,),
            ).fetchone()
            overview["limit_up"] = dict(row)

            # 大盘指数
            rows = conn.execute(
                """
                SELECT index_code, index_name, close_price, change_pct, amount
                FROM market_index_daily
                WHERE trade_date = ?
                ORDER BY index_code
                """,
                (trade_date,),
            ).fetchall()
            overview["market_index"] = [dict(r) for r in rows]

            # 情绪指标
            row = conn.execute(
                """
                SELECT limit_up_count, limit_down_count, highest_board
                FROM sentiment_daily
                WHERE trade_date = ?
                """,
                (trade_date,),
            ).fetchone()
            overview["sentiment"] = dict(row) if row else None

            return overview
        finally:
            conn.close()

    # ========== 涨停数据 ==========

    def get_limit_up_stocks(self, trade_date: str, plate_filter: str = None) -> list[dict]:
        """获取涨停股列表"""
        if plate_filter and plate_filter != "all":
            return self._query(
                """
                SELECT le.stock_code, le.stock_name, le.stock_price, le.up_limit_desc,
                       le.up_limit_time, le.up_limit_keep_times, le.reason, le.fengdan_money,
                       le.amount, lpm.plate_name, lpm.plate_code
                FROM limit_up_events le
                LEFT JOIN limit_up_plate_map lpm ON le.trade_date = lpm.trade_date AND le.stock_code = lpm.stock_code
                WHERE le.trade_date = ? AND lpm.plate_name = ?
                ORDER BY le.up_limit_time, le.stock_code
                """,
                (trade_date, plate_filter),
            )
        return self._query(
            """
            SELECT le.stock_code, le.stock_name, le.stock_price, le.up_limit_desc,
                   le.up_limit_time, le.up_limit_keep_times, le.reason, le.fengdan_money,
                   le.amount, lpm.plate_name, lpm.plate_code
            FROM limit_up_events le
            LEFT JOIN limit_up_plate_map lpm ON le.trade_date = lpm.trade_date AND le.stock_code = lpm.stock_code
            WHERE le.trade_date = ?
            ORDER BY le.up_limit_time, le.stock_code
            """,
            (trade_date,),
        )

    def get_limit_up_tiers(self, trade_date: str) -> list[dict]:
        """获取涨停梯队（按连板数分组）"""
        return self._query(
            """
            SELECT COALESCE(up_limit_desc, '首板') as tier,
                   COUNT(*) as count,
                   GROUP_CONCAT(stock_name, ', ') as stocks
            FROM limit_up_events
            WHERE trade_date = ?
            GROUP BY COALESCE(up_limit_desc, '首板')
            ORDER BY COALESCE(MAX(up_limit_keep_times), 1) DESC, COUNT(*) DESC
            """,
            (trade_date,),
        )

    # ========== 板块数据 ==========

    def get_hot_plates(self, trade_date: str, limit: int = 10) -> list[dict]:
        """获取热门板块排名"""
        return self._query(
            """
            SELECT rank_no, plate_code, plate_name, score
            FROM plate_hot_rank
            WHERE trade_date = ? AND source = 'uplimit_hot'
            ORDER BY rank_no
            LIMIT ?
            """,
            (trade_date, limit),
        )

    def get_plate_stocks(self, trade_date: str) -> list[dict]:
        """获取板块覆盖涨停股统计"""
        return self._query(
            """
            SELECT plate_name, plate_code, COUNT(DISTINCT stock_code) as stock_count
            FROM limit_up_plate_map
            WHERE trade_date = ?
            GROUP BY plate_name, plate_code
            ORDER BY stock_count DESC, plate_name
            """,
            (trade_date,),
        )

    def get_plate_trend(self, plate_code: str, days: int = 20) -> list[dict]:
        """获取板块趋势数据"""
        return self._query(
            """
            SELECT trade_date, plate_name, open_price, high_price, low_price,
                   close_price, change_pct, amount
            FROM plate_trends
            WHERE plate_code = ?
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (plate_code, days),
        )

    # ========== 龙虎榜 ==========

    def get_lhb(self, trade_date: str) -> list[dict]:
        """获取龙虎榜数据"""
        return self._query(
            """
            SELECT stock_code, stock_name, reason, buy_amount, sell_amount, net_buy_amount
            FROM lhb_daily
            WHERE trade_date = ?
            ORDER BY ABS(net_buy_amount) DESC
            """,
            (trade_date,),
        )

    # ========== 异动 ==========

    def get_alerts(self, trade_date: str, limit: int = 50) -> list[dict]:
        """获取盘中异动"""
        return self._query(
            """
            SELECT alert_time, stock_code, stock_name, alert_type, alert_text, price, change_pct
            FROM movement_alerts
            WHERE trade_date = ?
            ORDER BY alert_time DESC
            LIMIT ?
            """,
            (trade_date, limit),
        )

    # ========== 市场热点 ==========

    def get_market_hot(self, trade_date: str) -> list[dict]:
        """获取市场热点"""
        return self._query(
            """
            SELECT item_key, item_name, score, rank_no
            FROM market_hot_daily
            WHERE trade_date = ?
            ORDER BY rank_no
            """,
            (trade_date,),
        )

    # ========== 历史对比 ==========

    def get_limit_up_history(self, days: int = 15) -> list[dict]:
        """获取历史涨停数量趋势"""
        return self._query(
            """
            SELECT trade_date, COUNT(*) as stock_count,
                   COUNT(DISTINCT lpm.plate_code) as plate_count
            FROM limit_up_events le
            LEFT JOIN limit_up_plate_map lpm ON le.trade_date = lpm.trade_date
            GROUP BY le.trade_date
            ORDER BY le.trade_date DESC
            LIMIT ?
            """,
            (days,),
        )

    # ========== 复盘报告 ==========

    def get_daily_review(self, trade_date: str) -> dict | None:
        """获取已保存的复盘报告"""
        return self._query_one(
            "SELECT * FROM daily_reviews WHERE trade_date = ?",
            (trade_date,),
        )


def json_response(handler: BaseHTTPRequestHandler, status: int, data: dict | list):
    """发送 JSON 响应"""
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def create_server(host: str, port: int, db_path: str | Path) -> ThreadingHTTPServer:
    reader = MarketDBReader(db_path)

    class APIHandler(BaseHTTPRequestHandler):

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            params = parse_qs(parsed.query)

            try:
                status, data = self._route(path, params)
            except Exception as e:
                status, data = 500, {"error": str(e)}

            json_response(self, status, data)

        def do_OPTIONS(self) -> None:
            """CORS 预检"""
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def _route(self, path: str, params: dict) -> tuple[int, dict | list]:
            """路由分发"""

            # /api/dates
            if path == "/api/dates":
                limit = int(params.get("limit", [20])[0])
                return 200, {"dates": reader.get_trade_dates(limit)}

            # /api/review/overview?date=2026-06-01
            if path == "/api/review/overview":
                date = params.get("date", [None])[0]
                if not date:
                    return 400, {"error": "missing 'date' param"}
                return 200, reader.get_review_overview(date)

            # /api/review/limit-up?date=2026-06-01&plate=xxx
            if path == "/api/review/limit-up":
                date = params.get("date", [None])[0]
                if not date:
                    return 400, {"error": "missing 'date' param"}
                plate = params.get("plate", [None])[0]
                return 200, reader.get_limit_up_stocks(date, plate)

            # /api/review/tiers?date=2026-06-01
            if path == "/api/review/tiers":
                date = params.get("date", [None])[0]
                if not date:
                    return 400, {"error": "missing 'date' param"}
                return 200, reader.get_limit_up_tiers(date)

            # /api/review/hot-plates?date=2026-06-01&limit=10
            if path == "/api/review/hot-plates":
                date = params.get("date", [None])[0]
                limit = int(params.get("limit", [10])[0])
                if not date:
                    return 400, {"error": "missing 'date' param"}
                return 200, reader.get_hot_plates(date, limit)

            # /api/review/plate-stocks?date=2026-06-01
            if path == "/api/review/plate-stocks":
                date = params.get("date", [None])[0]
                if not date:
                    return 400, {"error": "missing 'date' param"}
                return 200, reader.get_plate_stocks(date)

            # /api/plate/trend?code=xxx&days=20
            if path == "/api/plate/trend":
                code = params.get("code", [None])[0]
                days = int(params.get("days", [20])[0])
                if not code:
                    return 400, {"error": "missing 'code' param"}
                return 200, reader.get_plate_trend(code, days)

            # /api/review/lhb?date=2026-06-01
            if path == "/api/review/lhb":
                date = params.get("date", [None])[0]
                if not date:
                    return 400, {"error": "missing 'date' param"}
                return 200, reader.get_lhb(date)

            # /api/review/alerts?date=2026-06-01&limit=50
            if path == "/api/review/alerts":
                date = params.get("date", [None])[0]
                limit = int(params.get("limit", [50])[0])
                if not date:
                    return 400, {"error": "missing 'date' param"}
                return 200, reader.get_alerts(date, limit)

            # /api/review/market-hot?date=2026-06-01
            if path == "/api/review/market-hot":
                date = params.get("date", [None])[0]
                if not date:
                    return 400, {"error": "missing 'date' param"}
                return 200, reader.get_market_hot(date)

            # /api/review/history?days=15
            if path == "/api/review/history":
                days = int(params.get("days", [15])[0])
                return 200, reader.get_limit_up_history(days)

            # /api/review/report?date=2026-06-01
            if path == "/api/review/report":
                date = params.get("date", [None])[0]
                if not date:
                    return 400, {"error": "missing 'date' param"}
                review = reader.get_daily_review(date)
                if not review:
                    return 404, {"error": "no review for this date"}
                return 200, review

            return 404, {"error": f"not found: {path}"}

        def log_message(self, format: str, *args) -> None:
            return

    return ThreadingHTTPServer((host, port), APIHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Market data API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.db)
    print(f"API server running at http://{args.host}:{server.server_address[1]}")
    print(f"Database: {args.db}")
    print(f"\nEndpoints:")
    print(f"  GET /api/dates")
    print(f"  GET /api/review/overview?date=YYYY-MM-DD")
    print(f"  GET /api/review/limit-up?date=YYYY-MM-DD[&plate=xxx]")
    print(f"  GET /api/review/tiers?date=YYYY-MM-DD")
    print(f"  GET /api/review/hot-plates?date=YYYY-MM-DD[&limit=10]")
    print(f"  GET /api/review/plate-stocks?date=YYYY-MM-DD")
    print(f"  GET /api/plate/trend?code=xxx[&days=20]")
    print(f"  GET /api/review/lhb?date=YYYY-MM-DD")
    print(f"  GET /api/review/alerts?date=YYYY-MM-DD[&limit=50]")
    print(f"  GET /api/review/market-hot?date=YYYY-MM-DD")
    print(f"  GET /api/review/history[?days=15]")
    print(f"  GET /api/review/report?date=YYYY-MM-DD")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
```

### 4.2 API 接口汇总

| 方法 | 路径 | 入参 | 出参 | 说明 |
|------|------|------|------|------|
| GET | `/api/dates` | `limit` (可选) | `{dates: ["2026-06-01", ...]}` | 有数据的交易日列表 |
| GET | `/api/review/overview` | `date` | `{limit_up: {...}, market_index: [...], sentiment: {...}}` | 每日复盘概览 |
| GET | `/api/review/limit-up` | `date`, `plate`(可选) | `[{stock_code, stock_name, ...}]` | 涨停股列表 |
| GET | `/api/review/tiers` | `date` | `[{tier, count, stocks}]` | 涨停梯队分组 |
| GET | `/api/review/hot-plates` | `date`, `limit`(可选) | `[{rank_no, plate_code, plate_name, score}]` | 热门板块排名 |
| GET | `/api/review/plate-stocks` | `date` | `[{plate_name, stock_count}]` | 板块覆盖涨停股统计 |
| GET | `/api/plate/trend` | `code`, `days`(可选) | `[{trade_date, close_price, change_pct, ...}]` | 板块趋势数据 |
| GET | `/api/review/lhb` | `date` | `[{stock_code, stock_name, buy_amount, ...}]` | 龙虎榜 |
| GET | `/api/review/alerts` | `date`, `limit`(可选) | `[{alert_time, stock_name, alert_text, ...}]` | 盘中异动 |
| GET | `/api/review/market-hot` | `date` | `[{item_name, score, rank_no}]` | 市场热点 |
| GET | `/api/review/history` | `days`(可选) | `[{trade_date, stock_count, plate_count}]` | 历史涨停趋势 |
| GET | `/api/review/report` | `date` | `{trade_date, summary, strongest_plates, ...}` | 已保存的复盘报告 |

## 五、报告生成层

### 5.1 generate_review.py 设计

```python
"""每日复盘报告生成器"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"
REPORT_DIR = PROJECT_ROOT / "reports"


class ReviewGenerator:
    """从数据库生成 Markdown 复盘报告"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def generate(self, trade_date: str) -> str:
        """生成完整的 Markdown 复盘报告"""
        sections = [
            self._header(trade_date),
            self._market_overview(trade_date),
            self._limit_up_summary(trade_date),
            self._tier_structure(trade_date),
            self._hot_plates(trade_date),
            self._plate_detail(trade_date),
            self._top_stocks(trade_date),
            self._lhb_summary(trade_date),
            self._alerts_summary(trade_date),
            self._history_compare(trade_date),
            self._footer(),
        ]
        return "\n\n".join(s for s in sections if s)

    def _query(self, sql: str, params=()) -> list[dict]:
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _query_one(self, sql: str, params=()) -> dict | None:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _header(self, trade_date: str) -> str:
        return f"# A股复盘报告 {trade_date}\n\n> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    def _market_overview(self, trade_date: str) -> str:
        """大盘指数概况"""
        indices = self._query(
            "SELECT index_name, close_price, change_pct FROM market_index_daily WHERE trade_date = ? ORDER BY index_code",
            (trade_date,),
        )
        if not indices:
            return "## 大盘指数\n\n暂无数据"

        lines = ["## 大盘指数\n"]
        for idx in indices:
            pct = idx["change_pct"] or 0
            arrow = "↑" if pct > 0 else "↓" if pct < 0 else "→"
            lines.append(f"- **{idx['index_name']}**: {idx['close_price']} ({arrow} {pct:+.2f}%)")
        return "\n".join(lines)

    def _limit_up_summary(self, trade_date: str) -> str:
        """涨停概况"""
        row = self._query_one(
            """
            SELECT
                COUNT(*) as total_stocks,
                COUNT(DISTINCT lpm.plate_code) as total_plates,
                SUM(CASE WHEN COALESCE(le.up_limit_desc, '') LIKE '%首板%' OR le.up_limit_desc IS NULL THEN 1 ELSE 0 END) as first_board,
                SUM(CASE WHEN le.up_limit_desc IS NOT NULL AND le.up_limit_desc NOT LIKE '%首板%' THEN 1 ELSE 0 END) as multi_board,
                MAX(le.up_limit_keep_times) as highest_board
            FROM limit_up_events le
            LEFT JOIN limit_up_plate_map lpm ON le.trade_date = lpm.trade_date AND le.stock_code = lpm.stock_code
            WHERE le.trade_date = ?
            """,
            (trade_date,),
        )
        if not row:
            return "## 涨停概况\n\n暂无数据"

        return f"""## 涨停概况

| 指标 | 数值 |
|------|------|
| 涨停股数 | {row['total_stocks']} |
| 涨停板块数 | {row['total_plates']} |
| 首板 | {row['first_board']} |
| 连板 | {row['multi_board']} |
| 最高板 | {row['highest_board']}板 |"""

    def _tier_structure(self, trade_date: str) -> str:
        """连板梯队结构"""
        tiers = self._query(
            """
            SELECT COALESCE(up_limit_desc, '首板') as tier, COUNT(*) as count,
                   GROUP_CONCAT(stock_name, '、') as names
            FROM limit_up_events
            WHERE trade_date = ?
            GROUP BY COALESCE(up_limit_desc, '首板')
            ORDER BY COALESCE(MAX(up_limit_keep_times), 1) DESC, COUNT(*) DESC
            """,
            (trade_date,),
        )
        if not tiers:
            return ""

        lines = ["## 连板梯队\n"]
        for t in tiers:
            lines.append(f"### {t['tier']} ({t['count']}只)\n")
            lines.append(f"{t['names']}\n")
        return "\n".join(lines)

    def _hot_plates(self, trade_date: str) -> str:
        """热门板块"""
        plates = self._query(
            """
            SELECT rank_no, plate_name, score
            FROM plate_hot_rank
            WHERE trade_date = ? AND source = 'uplimit_hot'
            ORDER BY rank_no
            LIMIT 10
            """,
            (trade_date,),
        )
        if not plates:
            return ""

        lines = ["## 热门板块 Top 10\n", "| 排名 | 板块 | 热度分 |", "|------|------|--------|"]
        for p in plates:
            lines.append(f"| {p['rank_no']} | {p['plate_name']} | {p['score']} |")
        return "\n".join(lines)

    def _plate_detail(self, trade_date: str) -> str:
        """板块涨停股分布"""
        plates = self._query(
            """
            SELECT plate_name, COUNT(DISTINCT stock_code) as stock_count,
                   GROUP_CONCAT(stock_name, '、') as stocks
            FROM limit_up_plate_map
            WHERE trade_date = ?
            GROUP BY plate_name
            ORDER BY stock_count DESC
            LIMIT 15
            """,
            (trade_date,),
        )
        if not plates:
            return ""

        lines = ["## 板块涨停股分布\n"]
        for p in plates:
            lines.append(f"**{p['plate_name']}** ({p['stock_count']}只): {p['stocks']}\n")
        return "\n".join(lines)

    def _top_stocks(self, trade_date: str) -> str:
        """核心涨停股"""
        stocks = self._query(
            """
            SELECT stock_name, stock_code, up_limit_desc, up_limit_time, reason
            FROM limit_up_events
            WHERE trade_date = ?
            ORDER BY COALESCE(up_limit_keep_times, 1) DESC, up_limit_time
            LIMIT 20
            """,
            (trade_date,),
        )
        if not stocks:
            return ""

        lines = ["## 核心涨停股\n", "| 股票 | 代码 | 梯队 | 时间 | 原因 |", "|------|------|------|------|------|"]
        for s in stocks:
            lines.append(
                f"| {s['stock_name']} | {s['stock_code']} | {s['up_limit_desc'] or '首板'} | {s['up_limit_time'] or '-'} | {(s['reason'] or '-')[:40]} |"
            )
        return "\n".join(lines)

    def _lhb_summary(self, trade_date: str) -> str:
        """龙虎榜摘要"""
        items = self._query(
            """
            SELECT stock_name, reason, net_buy_amount
            FROM lhb_daily
            WHERE trade_date = ?
            ORDER BY ABS(net_buy_amount) DESC
            LIMIT 10
            """,
            (trade_date,),
        )
        if not items:
            return ""

        lines = ["## 龙虎榜\n", "| 股票 | 原因 | 净买入(万) |", "|------|------|-----------|"]
        for item in items:
            net = item["net_buy_amount"] or 0
            lines.append(f"| {item['stock_name']} | {item['reason'] or '-'} | {net / 10000:.0f} |")
        return "\n".join(lines)

    def _alerts_summary(self, trade_date: str) -> str:
        """异动摘要"""
        alerts = self._query(
            """
            SELECT alert_time, stock_name, alert_text, change_pct
            FROM movement_alerts
            WHERE trade_date = ?
            ORDER BY alert_time DESC
            LIMIT 10
            """,
            (trade_date,),
        )
        if not alerts:
            return ""

        lines = ["## 盘中异动 (最近10条)\n"]
        for a in alerts:
            pct = f"{a['change_pct']:+.2f}%" if a["change_pct"] else ""
            lines.append(f"- `{a['alert_time']}` {a['stock_name']} {pct} - {a['alert_text']}")
        return "\n".join(lines)

    def _history_compare(self, trade_date: str) -> str:
        """历史对比"""
        history = self._query(
            """
            SELECT trade_date, COUNT(*) as count
            FROM limit_up_events
            GROUP BY trade_date
            ORDER BY trade_date DESC
            LIMIT 10
            """,
        )
        if not history:
            return ""

        lines = ["## 近10日涨停数量\n", "| 日期 | 涨停股数 |", "|------|----------|"]
        for h in history:
            marker = " **<-- 今日**" if h["trade_date"] == trade_date else ""
            lines.append(f"| {h['trade_date']} | {h['count']}{marker} |")
        return "\n".join(lines)

    def _footer(self) -> str:
        return "---\n*报告由「发家致富」系统自动生成*"

    def save_to_db(self, trade_date: str, report: str) -> None:
        """将复盘报告保存到 daily_reviews 表"""
        row = self._query_one(
            """
            SELECT
                COUNT(*) as total_stocks,
                COUNT(DISTINCT lpm.plate_code) as total_plates,
                SUM(CASE WHEN COALESCE(le.up_limit_desc, '') LIKE '%首板%' OR le.up_limit_desc IS NULL THEN 1 ELSE 0 END) as first_board,
                SUM(CASE WHEN le.up_limit_desc IS NOT NULL AND le.up_limit_desc NOT LIKE '%首板%' THEN 1 ELSE 0 END) as multi_board,
                MAX(le.up_limit_keep_times) as highest_board
            FROM limit_up_events le
            LEFT JOIN limit_up_plate_map lpm ON le.trade_date = lpm.trade_date AND le.stock_code = lpm.stock_code
            WHERE le.trade_date = ?
            """,
            (trade_date,),
        )

        hot_plates = self._query(
            "SELECT plate_name FROM plate_hot_rank WHERE trade_date = ? AND source = 'uplimit_hot' ORDER BY rank_no LIMIT 5",
            (trade_date,),
        )
        core_stocks = self._query(
            "SELECT stock_name FROM limit_up_events WHERE trade_date = ? ORDER BY COALESCE(up_limit_keep_times,1) DESC, up_limit_time LIMIT 10",
            (trade_date,),
        )

        self.conn.execute(
            """
            INSERT INTO daily_reviews(trade_date, limit_up_stock_count, limit_up_plate_count,
                first_board_count, multi_board_count, highest_board,
                strongest_plates, core_stocks, summary)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date) DO UPDATE SET
                limit_up_stock_count = excluded.limit_up_stock_count,
                limit_up_plate_count = excluded.limit_up_plate_count,
                first_board_count = excluded.first_board_count,
                multi_board_count = excluded.multi_board_count,
                highest_board = excluded.highest_board,
                strongest_plates = excluded.strongest_plates,
                core_stocks = excluded.core_stocks,
                summary = excluded.summary,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                trade_date,
                row["total_stocks"] if row else 0,
                row["total_plates"] if row else 0,
                row["first_board"] if row else 0,
                row["multi_board"] if row else 0,
                row["highest_board"] if row else 0,
                json.dumps([p["plate_name"] for p in hot_plates], ensure_ascii=False),
                json.dumps([s["stock_name"] for s in core_stocks], ensure_ascii=False),
                report,
            ),
        )
        self.conn.commit()


def write_report(trade_date: str, db_path: str | Path = DEFAULT_DB_PATH, output_dir: Path = REPORT_DIR) -> Path:
    """生成并保存报告"""
    gen = ReviewGenerator(db_path)
    try:
        report = gen.generate(trade_date)
        gen.save_to_db(trade_date, report)
    finally:
        gen.close()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"review-{trade_date}.md"
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate daily review report")
    parser.add_argument("--date", required=True, help="Trade date (YYYY-MM-DD)")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()

    path = write_report(args.date, args.db)
    print(f"Report saved to: {path}")


if __name__ == "__main__":
    main()
```

### 5.2 报告输出路径和命名

```
reports/
├── review-2026-06-01.md
├── review-2026-05-28.md
└── ...
```

报告同时写入两个位置：
1. `reports/review-{date}.md` -- 文件系统，便于直接查看
2. `daily_reviews` 表 -- 数据库，供 API 查询

## 六、前端看板改造

### 6.1 改造方案

将 `index.html` 从读取本地 JSON 文件改为调用 `data_server.py` 的 API 接口。

核心改动点：

1. **数据加载**：`fetch('data/uplimit/uplimit_${date}.json')` 改为 `fetch('/api/review/overview?date=${date}')` 等多个 API
2. **日期列表**：硬编码 dates 数组改为从 `/api/dates` 动态获取
3. **新增模块**：大盘指数、龙虎榜、异动、复盘报告

### 6.2 页面模块划分

```
+----------------------------------------------------------+
|  发家致富 - A股每日复盘                         [日期选择] |
+----------------------------------------------------------+
| [涨停股数] [涨停板块] [首板/连板] [最高板] [上证涨跌]     |
+----------------------------------------------------------+
| 涨停梯队 (左)          | 热门板块 Top 10 (右)             |
| 5板: XX, XX            | 1. 板块A ████████ 95             |
| 3板: XX, XX, XX        | 2. 板块B ██████ 82               |
| 2板: XX, XX, ...       | ...                              |
+----------------------------------------------------------+
| 涨停股明细表格 (全宽)                                     |
| [板块筛选器]                                              |
| 股票 | 代码 | 板块 | 时间 | 连板 | 原因                   |
+----------------------------------------------------------+
| 龙虎榜 (左)            | 盘中异动 (右)                    |
| 股票 | 净买入            | 时间 | 股票 | 异动             |
+----------------------------------------------------------+
| 复盘报告 (Markdown 渲染)                                  |
+----------------------------------------------------------+
| 历史涨停趋势 (折线/柱状)                                  |
+----------------------------------------------------------+
```

### 6.3 核心 JS 改造

```javascript
// 配置 API 地址
const API_BASE = 'http://127.0.0.1:8765';

// 状态管理
let currentDate = null;
let allStocks = [];

// 初始化
async function init() {
    // 从 API 获取可用日期
    const resp = await fetch(`${API_BASE}/api/dates`);
    const data = await resp.json();
    const dates = data.dates;

    const dateSelect = document.getElementById('dateSelect');
    dates.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d;
        opt.textContent = d;
        dateSelect.appendChild(opt);
    });
    dateSelect.onchange = () => loadData(dateSelect.value);

    if (dates.length > 0) {
        loadData(dates[0]);
    }
}

// 加载全部数据
async function loadData(date) {
    currentDate = date;

    // 并行请求所有数据
    const [overview, limitUp, tiers, hotPlates, plateStocks, lhb, alerts, report] = await Promise.all([
        fetchJSON(`/api/review/overview?date=${date}`),
        fetchJSON(`/api/review/limit-up?date=${date}`),
        fetchJSON(`/api/review/tiers?date=${date}`),
        fetchJSON(`/api/review/hot-plates?date=${date}&limit=10`),
        fetchJSON(`/api/review/plate-stocks?date=${date}`),
        fetchJSON(`/api/review/lhb?date=${date}`),
        fetchJSON(`/api/review/alerts?date=${date}&limit=20`),
        fetchJSON(`/api/review/report?date=${date}`).catch(() => null),
    ]);

    renderStats(overview);
    renderTiers(tiers);
    renderHotPlates(hotPlates);
    allStocks = limitUp;
    renderPlateFilter(plateStocks);
    renderStockTable();
    renderLHB(lhb);
    renderAlerts(alerts);
    renderReport(report);
}

async function fetchJSON(path) {
    const resp = await fetch(`${API_BASE}${path}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

// renderStats, renderTiers, renderHotPlates, renderStockTable 等
// 与现有逻辑类似，只是数据源从 currentData.xxx 改为 API 返回值
```

### 6.4 日期列表从 API 获取

现有硬编码的 dates 数组完全移除，改为页面加载时调用 `/api/dates` 动态获取。

## 七、定时调度

### 7.1 调度方案

使用 APScheduler 实现，也可以用系统 cron。

```python
"""定时调度入口 schedule_daily.py"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from fetch_daily import DailyFetcher
from generate_review import write_report
from api_client import QuantAPI
from db import MarketDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scheduler")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "market_review.db"
TOKEN_PATH = PROJECT_ROOT / "config" / "token.json"


def load_token() -> str:
    import json
    with open(TOKEN_PATH) as f:
        return json.load(f).get("token")


def daily_job():
    """每日收盘后执行的完整流程"""
    log.info("=" * 50)
    log.info("开始每日收盘复盘流程")

    # 1. 获取最近一个交易日
    token = load_token()
    if not token:
        log.error("未找到 token")
        return

    api = QuantAPI(token)
    db = MarketDB(DB_PATH)
    db.init_schema()

    today = datetime.now().strftime("%Y-%m-%d")
    trade_days = api.get_trade_days(today, days=5)
    if not trade_days:
        log.error("获取交易日历失败")
        return

    # 取最近的交易日
    trade_date = trade_days[-1] if isinstance(trade_days[-1], str) else trade_days[-1].get("date")
    log.info(f"最近交易日: {trade_date}")

    try:
        # 2. 数据采集
        log.info("步骤 1/3: 数据采集")
        fetcher = DailyFetcher(api, db)
        results = fetcher.run(trade_date)
        log.info(f"采集结果: {results}")

        # 3. 生成复盘报告
        log.info("步骤 2/3: 生成复盘报告")
        report_path = write_report(trade_date, DB_PATH)
        log.info(f"报告已保存: {report_path}")

        # 4. 生成 HTML 预览 (可选)
        log.info("步骤 3/3: 完成")
        log.info(f"复盘完成: {trade_date}")

    except Exception as e:
        log.error(f"流程执行失败: {e}", exc_info=True)
    finally:
        db.close()


def main():
    scheduler = BlockingScheduler()

    # 每个交易日 15:30 执行（A股收盘后30分钟）
    # 周一到周五，15:30
    scheduler.add_job(
        daily_job,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=30),
        id="daily_review",
        name="每日收盘复盘",
    )

    log.info("调度器已启动，等待下一个交易日 15:30 执行...")
    log.info("如需立即执行一次，请运行: python fetch_daily.py --date 2026-06-01")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("调度器已停止")


if __name__ == "__main__":
    main()
```

### 7.2 系统 cron 替代方案

如果不想引入 APScheduler 依赖，也可以用系统 crontab：

```bash
# 编辑 crontab
crontab -e

# 每周一到周五 15:30 执行
30 15 * * 1-5 cd /Users/admin/Desktop/obsidian/热爱生活/发家致富 && python src/fetch_daily.py --date $(date +\%Y-\%m-\%d) && python src/generate_review.py --date $(date +\%Y-\%m-\%d)
```

### 7.3 执行流程

```
15:30 触发
    |
    v
fetch_daily.py
    |-- 1. 获取最近交易日 (get_trade_days)
    |-- 2. 大盘指数 (get_index_trends)
    |-- 3. 涨停数据 (get_uplimit_reason + get_uplimit_hot + get_plate_rank)
    |-- 4. 龙虎榜 (get_lhb)
    |-- 5. 盘中异动 (get_alerts)
    |-- 6. 情绪K线 (get_sentiment_kline)
    |-- 7. 市场热点 (get_market_hot)
    |-- 8. 热门板块趋势 (get_plate_trend, Top 10)
    v
generate_review.py
    |-- 1. 从 DB 读取当日数据
    |-- 2. 生成 Markdown 报告
    |-- 3. 保存到 reports/ 目录
    |-- 4. 保存到 daily_reviews 表
    v
完成 (前端通过 data_server.py API 访问)
```

## 八、最终目录结构

```
发家致富/
├── index.html                    # 前端看板（调用 API）
├── src/
│   ├── api_client.py             # quant API 客户端（已有 + 新增方法）
│   ├── db.py                     # SQLite 表结构和写入（已有 + 新增方法）
│   ├── db_inventory.py           # 数据库元数据管理
│   ├── fetch_daily.py            # [新增] 每日数据采集脚本
│   ├── fetch_uplimit.py          # [保留] 涨停数据独立爬取（历史用）
│   ├── generate_review.py        # [新增] Markdown 复盘报告生成
│   ├── data_server.py            # [重构] RESTful JSON API 服务
│   ├── build_data_preview_html.py # [保留] HTML 预览页生成
│   ├── migrate_json_to_db.py     # [保留] JSON->SQLite 迁移
│   └── schedule_daily.py         # [新增] 定时调度入口
├── config/
│   ├── settings.yaml             # 配置文件
│   └── token.json                # API token
├── data/
│   ├── market_review.db          # SQLite 数据库
│   └── uplimit/                  # 旧 JSON 数据（归档）
├── reports/                      # [新增] Markdown 复盘报告
│   ├── review-2026-06-01.md
│   ├── review-2026-05-28.md
│   └── ...
└── docs/                         # HTML 预览页
```

## 九、实施顺序

按照依赖关系，建议按以下顺序编码：

| 阶段 | 任务 | 文件 | 依赖 |
|------|------|------|------|
| 1 | db.py 新增写入方法 | `db.py` | 无 |
| 2 | fetch_daily.py 数据采集 | `fetch_daily.py` | 阶段 1 |
| 3 | data_server.py API 重构 | `data_server.py` | 阶段 1 |
| 4 | generate_review.py 报告生成 | `generate_review.py` | 阶段 1 |
| 5 | index.html 前端改造 | `index.html` | 阶段 3 |
| 6 | schedule_daily.py 定时调度 | `schedule_daily.py` | 阶段 2, 4 |

阶段 1 是基础，完成后可以并行推进阶段 2/3/4。

---

以上是完整的技术方案，覆盖了从数据采集到前端展示的全链路。每个文件的代码都具体到可以直接开始编码的程度。如果需要我开始实现某个具体模块，请告诉我从哪个阶段开始。