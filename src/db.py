"""SQLite storage for market review data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def _json_ready(value: Any) -> Any:
    """Convert pandas/numpy-ish values into JSON-safe Python values."""
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        pass
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if hasattr(value, "item"):
        try:
            return _json_ready(value.item())
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def _json_text(value: Any) -> str:
    return json.dumps(_json_ready(value), ensure_ascii=False, default=str)


class MarketDB:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            pragma foreign_keys = on;

            create table if not exists trade_calendar (
                trade_date text primary key,
                is_trade_day integer not null default 1,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            );

            create table if not exists stocks (
                stock_code text primary key,
                stock_name text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            );

            create table if not exists plates (
                plate_code text primary key,
                plate_name text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            );

            create table if not exists raw_api_responses (
                id integer primary key autoincrement,
                trade_date text,
                source text not null,
                endpoint text not null,
                params_hash text not null,
                payload text not null,
                created_at text not null default current_timestamp,
                unique(trade_date, source, endpoint, params_hash)
            );

            create table if not exists limit_up_events (
                trade_date text not null,
                stock_code text not null,
                stock_name text,
                stock_price real,
                up_limit_desc text,
                up_limit_keep_times integer,
                up_limit_type text,
                up_limit_time text,
                reason text,
                fengdan_money real,
                fengdan_rate real,
                turnover_rate real,
                circulation_value real,
                market_type text,
                amount real,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, stock_code)
            );

            create table if not exists limit_up_plate_map (
                trade_date text not null,
                stock_code text not null,
                plate_code text not null,
                plate_name text,
                plate_score real,
                stock_reason text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, stock_code, plate_code)
            );

            create table if not exists plate_hot_rank (
                trade_date text not null,
                plate_code text not null,
                plate_name text,
                score real,
                rank_no integer not null,
                source text not null default 'uplimit_hot',
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, plate_code, source)
            );

            create table if not exists plate_daily (
                trade_date text not null,
                plate_code text not null,
                plate_name text,
                rank_no integer,
                score real,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, plate_code)
            );

            create table if not exists plate_trends (
                plate_code text not null,
                trade_date text not null,
                plate_name text,
                open_price real,
                high_price real,
                low_price real,
                close_price real,
                change_pct real,
                amount real,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(plate_code, trade_date)
            );

            create table if not exists plate_index_daily (
                plate_code text not null,
                trade_date text not null,
                plate_name text,
                board_type text,
                source text,
                open_price real,
                high_price real,
                low_price real,
                close_price real,
                change_pct real,
                volume real,
                amount real,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(plate_code, trade_date, source)
            );

            create table if not exists plate_reasons (
                plate_code text primary key,
                plate_name text,
                reason text,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            );

            create table if not exists lhb_daily (
                trade_date text not null,
                stock_code text not null,
                stock_name text,
                reason text,
                buy_amount real,
                sell_amount real,
                net_buy_amount real,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, stock_code, reason)
            );

            create table if not exists movement_alerts (
                trade_date text not null,
                alert_time text not null,
                stock_code text not null,
                stock_name text,
                alert_type text,
                alert_text text,
                price real,
                change_pct real,
                raw_hash text not null,
                raw_payload text,
                created_at text not null default current_timestamp,
                primary key(trade_date, alert_time, stock_code, raw_hash)
            );

            create table if not exists market_index_daily (
                trade_date text not null,
                index_code text not null,
                index_name text,
                close_price real,
                change_pct real,
                amount real,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, index_code)
            );

            create table if not exists sentiment_daily (
                trade_date text not null,
                period integer not null default 0,
                limit_up_count integer,
                limit_down_count integer,
                highest_board integer,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, period)
            );

            create table if not exists market_breadth_daily (
                trade_date text primary key,
                total_count integer,
                up_count integer,
                down_count integer,
                flat_count integer,
                limit_up_count integer,
                limit_down_count integer,
                natural_limit_up_count integer,
                natural_limit_down_count integer,
                avg_change_pct real,
                amount real,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            );

            create table if not exists limit_down_events (
                trade_date text not null,
                stock_code text not null,
                stock_name text,
                latest_price real,
                change_pct real,
                amount real,
                circulation_value real,
                total_market_cap real,
                turnover_rate real,
                seal_amount real,
                last_limit_down_time text,
                limit_down_days integer,
                open_count integer,
                industry text,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, stock_code)
            );

            create table if not exists broken_limit_up_events (
                trade_date text not null,
                stock_code text not null,
                stock_name text,
                latest_price real,
                change_pct real,
                limit_up_price real,
                amount real,
                circulation_value real,
                total_market_cap real,
                turnover_rate real,
                first_limit_up_time text,
                open_count integer,
                limit_up_stat text,
                amplitude real,
                industry text,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, stock_code)
            );

            create table if not exists market_hot_daily (
                trade_date text not null,
                item_key text not null,
                item_name text,
                score real,
                rank_no integer,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, item_key)
            );

            create table if not exists stock_kline_daily (
                stock_code text not null,
                trade_date text not null,
                open_price real,
                high_price real,
                low_price real,
                close_price real,
                volume real,
                amount real,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(stock_code, trade_date)
            );

            create table if not exists stock_trends (
                stock_code text not null,
                trade_date text not null,
                point_time text not null,
                price real,
                volume real,
                amount real,
                raw_payload text,
                created_at text not null default current_timestamp,
                primary key(stock_code, trade_date, point_time)
            );

            create table if not exists stock_info_snapshots (
                stock_code text not null,
                snapshot_date text not null,
                stock_name text,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(stock_code, snapshot_date)
            );

            create table if not exists daily_reviews (
                trade_date text primary key,
                limit_up_stock_count integer,
                limit_up_plate_count integer,
                first_board_count integer,
                multi_board_count integer,
                highest_board integer,
                strongest_plates text,
                core_stocks text,
                risk_flags text,
                opportunities text,
                next_plan text,
                markdown_path text,
                raw_payload text,
                summary text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
            );

            create table if not exists data_jobs (
                id integer primary key autoincrement,
                job_name text not null,
                trade_date text,
                status text not null,
                message text,
                details text,
                started_at text,
                finished_at text,
                created_at text not null default current_timestamp
            );

            create index if not exists idx_limit_up_events_date_time
                on limit_up_events(trade_date, up_limit_time);
            create index if not exists idx_limit_up_plate_map_date_plate
                on limit_up_plate_map(trade_date, plate_code);
            create index if not exists idx_plate_hot_rank_date_rank
                on plate_hot_rank(trade_date, rank_no);
            create index if not exists idx_plate_daily_date_rank
                on plate_daily(trade_date, rank_no);
            create index if not exists idx_plate_index_daily_date
                on plate_index_daily(trade_date);
            create index if not exists idx_raw_api_responses_endpoint
                on raw_api_responses(endpoint, trade_date);
            create index if not exists idx_movement_alerts_date_time
                on movement_alerts(trade_date, alert_time);
            create index if not exists idx_lhb_daily_date
                on lhb_daily(trade_date);
            create index if not exists idx_stock_kline_daily_date
                on stock_kline_daily(trade_date);
            create index if not exists idx_market_breadth_date
                on market_breadth_daily(trade_date);
            create index if not exists idx_limit_down_events_date
                on limit_down_events(trade_date);
            create index if not exists idx_broken_limit_up_events_date
                on broken_limit_up_events(trade_date);

            create table if not exists hot_stocks (
                trade_date text not null,
                rank_no integer not null,
                stock_code text not null,
                stock_name text,
                latest_price real,
                change_pct real,
                change_amount real,
                amount real,
                turnover_rate real,
                source text,
                raw_payload text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, stock_code)
            );

            create table if not exists hot_boards (
                trade_date text not null,
                board_type text not null,
                rank_no integer not null,
                board_code text not null,
                board_name text,
                latest_price real,
                change_pct real,
                change_amount real,
                total_market_cap real,
                turnover_rate real,
                up_count integer,
                down_count integer,
                leading_stock text,
                leading_stock_change real,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                primary key(trade_date, board_type, board_code)
            );

            create index if not exists idx_hot_stocks_date_rank
                on hot_stocks(trade_date, rank_no);
            create index if not exists idx_hot_boards_date_type_rank
                on hot_boards(trade_date, board_type, rank_no);
            """
        )
        self._ensure_daily_review_columns()
        self._ensure_data_job_columns()
        self._ensure_market_breadth_columns()
        self._ensure_hot_stock_columns()
        self.conn.commit()

    def _ensure_table_columns(self, table_name: str, columns: dict[str, str]) -> None:
        existing = {
            row["name"]
            for row in self.conn.execute(f"pragma table_info({table_name})").fetchall()
        }
        for name, column_type in columns.items():
            if name not in existing:
                self.conn.execute(f"alter table {table_name} add column {name} {column_type}")

    def _ensure_daily_review_columns(self) -> None:
        """Add new report columns when upgrading an existing database."""
        self._ensure_table_columns("daily_reviews", {
            "risk_flags": "text",
            "opportunities": "text",
            "next_plan": "text",
            "markdown_path": "text",
            "raw_payload": "text",
        })

    def _ensure_data_job_columns(self) -> None:
        """Add job tracking columns when upgrading an existing database."""
        self._ensure_table_columns("data_jobs", {
            "details": "text",
            "started_at": "text",
            "finished_at": "text",
        })

    def _ensure_market_breadth_columns(self) -> None:
        """Add breadth metrics needed by review-home trend charts."""
        self._ensure_table_columns("market_breadth_daily", {
            "natural_limit_up_count": "integer",
            "natural_limit_down_count": "integer",
            "avg_change_pct": "real",
        })

    def _ensure_hot_stock_columns(self) -> None:
        """Add richer hot-rank fields for popularity emotion analysis."""
        self._ensure_table_columns("hot_stocks", {
            "amount": "real",
            "turnover_rate": "real",
            "source": "text",
            "raw_payload": "text",
        })


    def import_uplimit_day(self, day_data: dict[str, Any], raw_source: str = "json") -> None:
        trade_date = day_data["date"]
        self._upsert_trade_day(trade_date)
        self._store_raw_response(
            trade_date=trade_date,
            source=raw_source,
            endpoint="uplimit_day",
            params={"date": trade_date},
            payload=day_data,
        )

        for plate in day_data.get("uplimit_reason") or []:
            plate_code = str(plate.get("plate_code") or "")
            plate_name = plate.get("plate_name")
            plate_score = plate.get("plate_score")
            if plate_code:
                self._upsert_plate(plate_code, plate_name)

            for stock in plate.get("stocks") or []:
                stock_code = str(stock.get("stock_code") or "")
                if not stock_code:
                    continue

                stock_name = stock.get("stock_name")
                self._upsert_stock(stock_code, stock_name)
                self._upsert_limit_up_event(trade_date, stock)
                if plate_code:
                    self._upsert_limit_up_plate_map(
                        trade_date=trade_date,
                        stock_code=stock_code,
                        plate_code=plate_code,
                        plate_name=plate_name,
                        plate_score=plate_score,
                        stock_reason=stock.get("reason"),
                    )

        for rank_no, item in enumerate(day_data.get("uplimit_hot") or [], start=1):
            parsed = self._parse_hot_plate(item)
            if parsed is None:
                continue
            plate_name, plate_code, score = parsed
            self._upsert_plate(plate_code, plate_name)
            self.conn.execute(
                """
                insert into plate_hot_rank(trade_date, plate_code, plate_name, score, rank_no, source)
                values(?, ?, ?, ?, ?, 'uplimit_hot')
                on conflict(trade_date, plate_code, source) do update set
                    plate_name = excluded.plate_name,
                    score = excluded.score,
                    rank_no = excluded.rank_no,
                    updated_at = current_timestamp
                """,
                (trade_date, plate_code, plate_name, score, rank_no),
            )

        for rank_no, item in enumerate(day_data.get("plate_rank") or [], start=1):
            plate_code = str(item.get("plate_code") or item.get("code") or "")
            plate_name = item.get("plate_name") or item.get("name")
            if not plate_code:
                continue
            self._upsert_plate(plate_code, plate_name)
            score = item.get("plate_score") or item.get("score") or item.get("amount")
            self.conn.execute(
                """
                insert into plate_daily(trade_date, plate_code, plate_name, rank_no, score, raw_payload)
                values(?, ?, ?, ?, ?, ?)
                on conflict(trade_date, plate_code) do update set
                    plate_name = excluded.plate_name,
                    rank_no = excluded.rank_no,
                    score = excluded.score,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (trade_date, plate_code, plate_name, rank_no, score, json.dumps(item, ensure_ascii=False)),
            )

        self.conn.commit()

    def _upsert_trade_day(self, trade_date: str) -> None:
        self.conn.execute(
            """
            insert into trade_calendar(trade_date, is_trade_day)
            values(?, 1)
            on conflict(trade_date) do update set
                is_trade_day = excluded.is_trade_day,
                updated_at = current_timestamp
            """,
            (trade_date,),
        )

    def _upsert_stock(self, stock_code: str, stock_name: str | None) -> None:
        self.conn.execute(
            """
            insert into stocks(stock_code, stock_name)
            values(?, ?)
            on conflict(stock_code) do update set
                stock_name = coalesce(excluded.stock_name, stocks.stock_name),
                updated_at = current_timestamp
            """,
            (stock_code, stock_name),
        )

    def _upsert_plate(self, plate_code: str, plate_name: str | None) -> None:
        self.conn.execute(
            """
            insert into plates(plate_code, plate_name)
            values(?, ?)
            on conflict(plate_code) do update set
                plate_name = coalesce(excluded.plate_name, plates.plate_name),
                updated_at = current_timestamp
            """,
            (plate_code, plate_name),
        )

    def _upsert_limit_up_event(self, trade_date: str, stock: dict[str, Any]) -> None:
        self.conn.execute(
            """
            insert into limit_up_events(
                trade_date, stock_code, stock_name, stock_price, up_limit_desc,
                up_limit_keep_times, up_limit_type, up_limit_time, reason,
                fengdan_money, fengdan_rate, turnover_rate, circulation_value,
                market_type, amount
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(trade_date, stock_code) do update set
                stock_name = excluded.stock_name,
                stock_price = coalesce(excluded.stock_price, limit_up_events.stock_price),
                up_limit_desc = coalesce(excluded.up_limit_desc, limit_up_events.up_limit_desc),
                up_limit_keep_times = coalesce(excluded.up_limit_keep_times, limit_up_events.up_limit_keep_times),
                up_limit_type = coalesce(excluded.up_limit_type, limit_up_events.up_limit_type),
                up_limit_time = coalesce(excluded.up_limit_time, limit_up_events.up_limit_time),
                reason = coalesce(excluded.reason, limit_up_events.reason),
                fengdan_money = coalesce(excluded.fengdan_money, limit_up_events.fengdan_money),
                fengdan_rate = coalesce(excluded.fengdan_rate, limit_up_events.fengdan_rate),
                turnover_rate = coalesce(excluded.turnover_rate, limit_up_events.turnover_rate),
                circulation_value = coalesce(excluded.circulation_value, limit_up_events.circulation_value),
                market_type = coalesce(excluded.market_type, limit_up_events.market_type),
                amount = coalesce(excluded.amount, limit_up_events.amount),
                updated_at = current_timestamp
            """,
            (
                trade_date,
                str(stock.get("stock_code") or ""),
                stock.get("stock_name"),
                stock.get("stock_price"),
                stock.get("up_limit_desc"),
                stock.get("up_limit_keep_times"),
                stock.get("up_limit_type"),
                stock.get("up_limit_time"),
                stock.get("reason"),
                stock.get("fengdan_money"),
                stock.get("fengdan_rate"),
                stock.get("turnover_ration_real"),
                stock.get("actualcirculation_value"),
                stock.get("market_type"),
                stock.get("amount"),
            ),
        )

    def _upsert_limit_up_plate_map(
        self,
        trade_date: str,
        stock_code: str,
        plate_code: str,
        plate_name: str | None,
        plate_score: Any,
        stock_reason: str | None,
    ) -> None:
        self.conn.execute(
            """
            insert into limit_up_plate_map(
                trade_date, stock_code, plate_code, plate_name, plate_score, stock_reason
            )
            values(?, ?, ?, ?, ?, ?)
            on conflict(trade_date, stock_code, plate_code) do update set
                plate_name = excluded.plate_name,
                plate_score = excluded.plate_score,
                stock_reason = excluded.stock_reason,
                updated_at = current_timestamp
            """,
            (trade_date, stock_code, plate_code, plate_name, plate_score, stock_reason),
        )

    def _store_raw_response(
        self,
        trade_date: str,
        source: str,
        endpoint: str,
        params: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        params_text = json.dumps(params, sort_keys=True, ensure_ascii=False)
        params_hash = hashlib.sha256(params_text.encode("utf-8")).hexdigest()
        payload_text = _json_text(payload)
        self.conn.execute(
            """
            insert into raw_api_responses(trade_date, source, endpoint, params_hash, payload)
            values(?, ?, ?, ?, ?)
            on conflict(trade_date, source, endpoint, params_hash) do update set
                payload = excluded.payload
            """,
            (trade_date, source, endpoint, params_hash, payload_text),
        )

    def import_index_daily(self, trade_date: str, indices: list[dict[str, Any]], raw_source: str = "api") -> int:
        """Import market index daily data. Returns number of rows upserted."""
        count = 0
        for idx in indices:
            index_code = idx.get("code") or idx.get("display_code", "")
            if not index_code:
                continue
            index_name = idx.get("name") or idx.get("display_name")
            close_price = idx.get("last_px")
            change_pct = idx.get("px_change_rate")
            amount = idx.get("amount")
            if amount is None:
                amount = idx.get("volume")
            self.conn.execute(
                """
                insert into market_index_daily(trade_date, index_code, index_name, close_price, change_pct, amount, raw_payload)
                values(?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, index_code) do update set
                    index_name = excluded.index_name,
                    close_price = excluded.close_price,
                    change_pct = excluded.change_pct,
                    amount = excluded.amount,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    trade_date,
                    index_code,
                    index_name,
                    close_price,
                    change_pct,
                    amount,
                    _json_text(idx),
                ),
            )
            count += 1
        self._store_raw_response(
            trade_date=trade_date,
            source=raw_source,
            endpoint="index_trends",
            params={"date": trade_date},
            payload={"indices": indices},
        )
        self.conn.commit()
        return count

    def import_sentiment_daily(self, kline_data: list[dict[str, Any]], period: int = 0, raw_source: str = "api") -> int:
        """Import sentiment kline data into sentiment_daily table. Returns number of rows upserted.

        The API returns OHLC-style sentiment index data:
        - p_open, p_high, p_low, p_close: sentiment index OHLC
        - amount: trading amount
        - date: trade date

        We also auto-populate limit_up_count from limit_up_events table
        if the data is available.
        """
        count = 0
        for item in kline_data:
            trade_date = item.get("date")
            if not trade_date:
                continue
            self._upsert_trade_day(trade_date)

            # Try to get limit_up_count from limit_up_events if not in API response
            limit_up_count = item.get("limit_up_count")
            if limit_up_count is None:
                row = self.conn.execute(
                    "select count(*) as cnt from limit_up_events where trade_date = ?",
                    (trade_date,),
                ).fetchone()
                if row:
                    limit_up_count = row["cnt"]

            self.conn.execute(
                """
                insert into sentiment_daily(trade_date, period, limit_up_count, limit_down_count, highest_board, raw_payload)
                values(?, ?, ?, ?, ?, ?)
                on conflict(trade_date, period) do update set
                    limit_up_count = coalesce(excluded.limit_up_count, sentiment_daily.limit_up_count),
                    limit_down_count = coalesce(excluded.limit_down_count, sentiment_daily.limit_down_count),
                    highest_board = coalesce(excluded.highest_board, sentiment_daily.highest_board),
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    trade_date,
                    period,
                    limit_up_count,
                    item.get("limit_down_count"),
                    item.get("highest_board"),
                    _json_text(item),
                ),
            )
            count += 1

        # Store raw response for the first date in the batch
        if kline_data:
            first_date = kline_data[0].get("date", "")
            self._store_raw_response(
                trade_date=first_date,
                source=raw_source,
                endpoint="sentiment_kline",
                params={"period": period},
                payload={"kline": kline_data},
            )
        self.conn.commit()
        return count

    def import_market_breadth(self, trade_date: str, snapshot: dict[str, Any]) -> int:
        """导入全市场涨跌家数和成交额快照。"""
        self._upsert_trade_day(trade_date)
        self.conn.execute(
            """
            insert into market_breadth_daily(
                trade_date, total_count, up_count, down_count, flat_count,
                limit_up_count, limit_down_count, natural_limit_up_count,
                natural_limit_down_count, avg_change_pct, amount, raw_payload
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(trade_date) do update set
                total_count = coalesce(excluded.total_count, market_breadth_daily.total_count),
                up_count = coalesce(excluded.up_count, market_breadth_daily.up_count),
                down_count = coalesce(excluded.down_count, market_breadth_daily.down_count),
                flat_count = coalesce(excluded.flat_count, market_breadth_daily.flat_count),
                limit_up_count = coalesce(excluded.limit_up_count, market_breadth_daily.limit_up_count),
                limit_down_count = coalesce(excluded.limit_down_count, market_breadth_daily.limit_down_count),
                natural_limit_up_count = coalesce(excluded.natural_limit_up_count, market_breadth_daily.natural_limit_up_count),
                natural_limit_down_count = coalesce(excluded.natural_limit_down_count, market_breadth_daily.natural_limit_down_count),
                avg_change_pct = coalesce(excluded.avg_change_pct, market_breadth_daily.avg_change_pct),
                amount = coalesce(excluded.amount, market_breadth_daily.amount),
                raw_payload = excluded.raw_payload,
                updated_at = current_timestamp
            """,
            (
                trade_date,
                snapshot.get("total_count"),
                snapshot.get("up_count"),
                snapshot.get("down_count"),
                snapshot.get("flat_count"),
                snapshot.get("limit_up_count"),
                snapshot.get("limit_down_count"),
                snapshot.get("natural_limit_up_count"),
                snapshot.get("natural_limit_down_count"),
                snapshot.get("avg_change_pct"),
                snapshot.get("amount"),
                _json_text(snapshot),
            ),
        )
        self.conn.commit()
        return 1

    def import_limit_down_events(self, trade_date: str, records: list[dict[str, Any]]) -> int:
        """导入跌停池数据。"""
        self._upsert_trade_day(trade_date)
        count = 0
        for r in records:
            stock_code = str(r.get("stock_code") or "")
            if not stock_code:
                continue
            self._upsert_stock(stock_code, r.get("stock_name"))
            self.conn.execute(
                """
                insert into limit_down_events(
                    trade_date, stock_code, stock_name, latest_price, change_pct,
                    amount, circulation_value, total_market_cap, turnover_rate,
                    seal_amount, last_limit_down_time, limit_down_days,
                    open_count, industry, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, stock_code) do update set
                    stock_name = excluded.stock_name,
                    latest_price = excluded.latest_price,
                    change_pct = excluded.change_pct,
                    amount = excluded.amount,
                    circulation_value = excluded.circulation_value,
                    total_market_cap = excluded.total_market_cap,
                    turnover_rate = excluded.turnover_rate,
                    seal_amount = excluded.seal_amount,
                    last_limit_down_time = excluded.last_limit_down_time,
                    limit_down_days = excluded.limit_down_days,
                    open_count = excluded.open_count,
                    industry = excluded.industry,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    trade_date,
                    stock_code,
                    r.get("stock_name"),
                    r.get("latest_price"),
                    r.get("change_pct"),
                    r.get("amount"),
                    r.get("circulation_value"),
                    r.get("total_market_cap"),
                    r.get("turnover_rate"),
                    r.get("seal_amount"),
                    r.get("last_limit_down_time"),
                    r.get("limit_down_days"),
                    r.get("open_count"),
                    r.get("industry"),
                    _json_text(r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_broken_limit_up_events(self, trade_date: str, records: list[dict[str, Any]]) -> int:
        """导入炸板池数据。"""
        self._upsert_trade_day(trade_date)
        count = 0
        for r in records:
            stock_code = str(r.get("stock_code") or "")
            if not stock_code:
                continue
            self._upsert_stock(stock_code, r.get("stock_name"))
            self.conn.execute(
                """
                insert into broken_limit_up_events(
                    trade_date, stock_code, stock_name, latest_price, change_pct,
                    limit_up_price, amount, circulation_value, total_market_cap,
                    turnover_rate, first_limit_up_time, open_count,
                    limit_up_stat, amplitude, industry, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, stock_code) do update set
                    stock_name = excluded.stock_name,
                    latest_price = excluded.latest_price,
                    change_pct = excluded.change_pct,
                    limit_up_price = excluded.limit_up_price,
                    amount = excluded.amount,
                    circulation_value = excluded.circulation_value,
                    total_market_cap = excluded.total_market_cap,
                    turnover_rate = excluded.turnover_rate,
                    first_limit_up_time = excluded.first_limit_up_time,
                    open_count = excluded.open_count,
                    limit_up_stat = excluded.limit_up_stat,
                    amplitude = excluded.amplitude,
                    industry = excluded.industry,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    trade_date,
                    stock_code,
                    r.get("stock_name"),
                    r.get("latest_price"),
                    r.get("change_pct"),
                    r.get("limit_up_price"),
                    r.get("amount"),
                    r.get("circulation_value"),
                    r.get("total_market_cap"),
                    r.get("turnover_rate"),
                    r.get("first_limit_up_time"),
                    r.get("open_count"),
                    r.get("limit_up_stat"),
                    r.get("amplitude"),
                    r.get("industry"),
                    _json_text(r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_lhb_daily(self, trade_date: str, records: list[dict[str, Any]]) -> int:
        """导入龙虎榜每日明细。"""
        self._upsert_trade_day(trade_date)
        count = 0
        for r in records:
            stock_code = str(r.get("stock_code") or "")
            reason = r.get("reason") or ""
            if not stock_code:
                continue
            self._upsert_stock(stock_code, r.get("stock_name"))
            self.conn.execute(
                """
                insert into lhb_daily(
                    trade_date, stock_code, stock_name, reason,
                    buy_amount, sell_amount, net_buy_amount, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, stock_code, reason) do update set
                    stock_name = excluded.stock_name,
                    buy_amount = excluded.buy_amount,
                    sell_amount = excluded.sell_amount,
                    net_buy_amount = excluded.net_buy_amount,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    trade_date,
                    stock_code,
                    r.get("stock_name"),
                    reason,
                    r.get("buy_amount"),
                    r.get("sell_amount"),
                    r.get("net_buy_amount"),
                    _json_text(r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_market_hot_daily(self, trade_date: str, records: list[dict[str, Any]]) -> int:
        """导入市场热点列表。"""
        self._upsert_trade_day(trade_date)
        count = 0
        for r in records:
            item_key = str(r.get("item_key") or r.get("item_name") or "")
            if not item_key:
                continue
            self.conn.execute(
                """
                insert into market_hot_daily(trade_date, item_key, item_name, score, rank_no, raw_payload)
                values(?, ?, ?, ?, ?, ?)
                on conflict(trade_date, item_key) do update set
                    item_name = excluded.item_name,
                    score = excluded.score,
                    rank_no = excluded.rank_no,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    trade_date,
                    item_key,
                    r.get("item_name"),
                    r.get("score"),
                    r.get("rank_no"),
                    _json_text(r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_movement_alerts(self, trade_date: str, records: list[dict[str, Any]]) -> int:
        """导入盘中异动提醒。"""
        self._upsert_trade_day(trade_date)
        count = 0
        for r in records:
            alert_time = str(r.get("alert_time") or "")
            stock_code = str(r.get("stock_code") or "")
            if not alert_time or not stock_code:
                continue
            self._upsert_stock(stock_code, r.get("stock_name"))
            raw_text = _json_text(r)
            raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            self.conn.execute(
                """
                insert into movement_alerts(
                    trade_date, alert_time, stock_code, stock_name, alert_type,
                    alert_text, price, change_pct, raw_hash, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, alert_time, stock_code, raw_hash) do nothing
                """,
                (
                    trade_date,
                    alert_time,
                    stock_code,
                    r.get("stock_name"),
                    r.get("alert_type"),
                    r.get("alert_text"),
                    r.get("price"),
                    r.get("change_pct"),
                    raw_hash,
                    raw_text,
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_stock_kline_daily(self, stock_code: str, records: list[dict[str, Any]]) -> int:
        """导入个股日 K 数据。"""
        stock_code = str(stock_code or "")
        if not stock_code:
            return 0
        count = 0
        for r in records:
            trade_date = r.get("trade_date")
            if not trade_date:
                continue
            self._upsert_trade_day(str(trade_date))
            self.conn.execute(
                """
                insert into stock_kline_daily(
                    stock_code, trade_date, open_price, high_price, low_price,
                    close_price, volume, amount, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(stock_code, trade_date) do update set
                    open_price = excluded.open_price,
                    high_price = excluded.high_price,
                    low_price = excluded.low_price,
                    close_price = excluded.close_price,
                    volume = excluded.volume,
                    amount = excluded.amount,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    stock_code,
                    str(trade_date),
                    r.get("open_price"),
                    r.get("high_price"),
                    r.get("low_price"),
                    r.get("close_price"),
                    r.get("volume"),
                    r.get("amount"),
                    _json_text(r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_daily_review(self, review: dict[str, Any]) -> int:
        """导入自动复盘结论。"""
        trade_date = str(review.get("trade_date") or "")
        if not trade_date:
            return 0
        self._upsert_trade_day(trade_date)
        self.conn.execute(
            """
            insert into daily_reviews(
                trade_date, limit_up_stock_count, limit_up_plate_count,
                first_board_count, multi_board_count, highest_board,
                strongest_plates, core_stocks, risk_flags, opportunities,
                next_plan, markdown_path, raw_payload, summary
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(trade_date) do update set
                limit_up_stock_count = excluded.limit_up_stock_count,
                limit_up_plate_count = excluded.limit_up_plate_count,
                first_board_count = excluded.first_board_count,
                multi_board_count = excluded.multi_board_count,
                highest_board = excluded.highest_board,
                strongest_plates = excluded.strongest_plates,
                core_stocks = excluded.core_stocks,
                risk_flags = excluded.risk_flags,
                opportunities = excluded.opportunities,
                next_plan = excluded.next_plan,
                markdown_path = excluded.markdown_path,
                raw_payload = excluded.raw_payload,
                summary = excluded.summary,
                updated_at = current_timestamp
            """,
            (
                trade_date,
                review.get("limit_up_stock_count"),
                review.get("limit_up_plate_count"),
                review.get("first_board_count"),
                review.get("multi_board_count"),
                review.get("highest_board"),
                _json_text(review.get("strongest_plates") or []),
                _json_text(review.get("core_stocks") or []),
                _json_text(review.get("risk_flags") or []),
                _json_text(review.get("opportunities") or []),
                _json_text(review.get("next_plan") or []),
                review.get("markdown_path"),
                _json_text(review),
                review.get("summary"),
            ),
        )
        self.conn.commit()
        return 1

    def import_hot_stocks(self, trade_date: str, records: list[dict[str, Any]]) -> int:
        """导入热门股票人气榜数据"""
        self._upsert_trade_day(trade_date)
        count = 0
        for r in records:
            stock_code = r.get("stock_code", "")
            if not stock_code:
                continue
            self._upsert_stock(stock_code, r.get("stock_name"))
            self.conn.execute(
                """
                insert into hot_stocks(
                    trade_date, rank_no, stock_code, stock_name, latest_price,
                    change_pct, change_amount, amount, turnover_rate, source, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, stock_code) do update set
                    rank_no = excluded.rank_no,
                    stock_name = excluded.stock_name,
                    latest_price = excluded.latest_price,
                    change_pct = excluded.change_pct,
                    change_amount = excluded.change_amount,
                    amount = coalesce(excluded.amount, hot_stocks.amount),
                    turnover_rate = coalesce(excluded.turnover_rate, hot_stocks.turnover_rate),
                    source = coalesce(excluded.source, hot_stocks.source),
                    raw_payload = coalesce(excluded.raw_payload, hot_stocks.raw_payload),
                    updated_at = current_timestamp
                """,
                (trade_date, r["rank_no"], stock_code, r.get("stock_name"),
                 r.get("latest_price"), r.get("change_pct"), r.get("change_amount"),
                 r.get("amount"), r.get("turnover_rate"), r.get("source"), _json_text(r.get("raw_payload") or r)),
            )
            count += 1
        self.conn.commit()
        return count

    def import_hot_boards(self, trade_date: str, records: list[dict[str, Any]], board_type: str) -> int:
        """导入热门板块数据（concept=概念板块, industry=行业板块）"""
        self._upsert_trade_day(trade_date)
        count = 0
        for r in records:
            board_code = r.get("board_code", "")
            if not board_code:
                board_code = f"ths_{r.get('board_name', '')}"
            self._upsert_plate(board_code, r.get("board_name"))
            self.conn.execute(
                """
                insert into hot_boards(trade_date, board_type, rank_no, board_code, board_name,
                    latest_price, change_pct, change_amount, total_market_cap, turnover_rate,
                    up_count, down_count, leading_stock, leading_stock_change)
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(trade_date, board_type, board_code) do update set
                    rank_no = excluded.rank_no,
                    board_name = excluded.board_name,
                    latest_price = excluded.latest_price,
                    change_pct = excluded.change_pct,
                    change_amount = excluded.change_amount,
                    total_market_cap = excluded.total_market_cap,
                    turnover_rate = excluded.turnover_rate,
                    up_count = excluded.up_count,
                    down_count = excluded.down_count,
                    leading_stock = excluded.leading_stock,
                    leading_stock_change = excluded.leading_stock_change,
                    updated_at = current_timestamp
                """,
                (trade_date, board_type, r["rank_no"], board_code, r.get("board_name"),
                 r.get("latest_price"), r.get("change_pct"), r.get("change_amount"),
                 r.get("total_market_cap"), r.get("turnover_rate"),
                 r.get("up_count"), r.get("down_count"),
                 r.get("leading_stock"), r.get("leading_stock_change")),
            )
            count += 1
        self.conn.commit()
        return count

    def import_plate_trends(self, records: list[dict[str, Any]]) -> int:
        """导入本地派生的板块强度趋势。"""
        count = 0
        for r in records:
            plate_code = str(r.get("plate_code") or "")
            trade_date = str(r.get("trade_date") or "")
            if not plate_code or not trade_date:
                continue
            plate_name = r.get("plate_name")
            self._upsert_trade_day(trade_date)
            self._upsert_plate(plate_code, plate_name)
            self.conn.execute(
                """
                insert into plate_trends(
                    plate_code, trade_date, plate_name, open_price, high_price,
                    low_price, close_price, change_pct, amount, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(plate_code, trade_date) do update set
                    plate_name = excluded.plate_name,
                    open_price = excluded.open_price,
                    high_price = excluded.high_price,
                    low_price = excluded.low_price,
                    close_price = excluded.close_price,
                    change_pct = excluded.change_pct,
                    amount = excluded.amount,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    plate_code,
                    trade_date,
                    plate_name,
                    r.get("open_price"),
                    r.get("high_price"),
                    r.get("low_price"),
                    r.get("close_price"),
                    r.get("change_pct"),
                    r.get("amount"),
                    _json_text(r.get("raw_payload") or r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_plate_index_daily(self, records: list[dict[str, Any]]) -> int:
        """导入真实板块指数日 K 数据。"""
        count = 0
        for r in records:
            plate_code = str(r.get("plate_code") or "")
            trade_date = str(r.get("trade_date") or "")
            source = str(r.get("source") or "")
            if not plate_code or not trade_date or not source:
                continue
            plate_name = r.get("plate_name")
            self._upsert_trade_day(trade_date)
            self._upsert_plate(plate_code, plate_name)
            self.conn.execute(
                """
                insert into plate_index_daily(
                    plate_code, trade_date, plate_name, board_type, source,
                    open_price, high_price, low_price, close_price, change_pct,
                    volume, amount, raw_payload
                )
                values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(plate_code, trade_date, source) do update set
                    plate_name = excluded.plate_name,
                    board_type = excluded.board_type,
                    open_price = excluded.open_price,
                    high_price = excluded.high_price,
                    low_price = excluded.low_price,
                    close_price = excluded.close_price,
                    change_pct = excluded.change_pct,
                    volume = excluded.volume,
                    amount = excluded.amount,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    plate_code,
                    trade_date,
                    plate_name,
                    r.get("board_type"),
                    source,
                    r.get("open_price"),
                    r.get("high_price"),
                    r.get("low_price"),
                    r.get("close_price"),
                    r.get("change_pct"),
                    r.get("volume"),
                    r.get("amount"),
                    _json_text(r.get("raw_payload") or r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_plate_reasons(self, records: list[dict[str, Any]]) -> int:
        """导入本地汇总的板块原因。"""
        count = 0
        for r in records:
            plate_code = str(r.get("plate_code") or "")
            if not plate_code:
                continue
            plate_name = r.get("plate_name")
            self._upsert_plate(plate_code, plate_name)
            self.conn.execute(
                """
                insert into plate_reasons(plate_code, plate_name, reason, raw_payload)
                values(?, ?, ?, ?)
                on conflict(plate_code) do update set
                    plate_name = excluded.plate_name,
                    reason = excluded.reason,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    plate_code,
                    plate_name,
                    r.get("reason"),
                    _json_text(r.get("raw_payload") or r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def import_stock_info_snapshots(self, records: list[dict[str, Any]]) -> int:
        """导入核心个股的本地资料快照。"""
        count = 0
        for r in records:
            stock_code = str(r.get("stock_code") or "")
            snapshot_date = str(r.get("snapshot_date") or r.get("trade_date") or "")
            if not stock_code or not snapshot_date:
                continue
            stock_name = r.get("stock_name")
            self._upsert_trade_day(snapshot_date)
            self._upsert_stock(stock_code, stock_name)
            self.conn.execute(
                """
                insert into stock_info_snapshots(stock_code, snapshot_date, stock_name, raw_payload)
                values(?, ?, ?, ?)
                on conflict(stock_code, snapshot_date) do update set
                    stock_name = excluded.stock_name,
                    raw_payload = excluded.raw_payload,
                    updated_at = current_timestamp
                """,
                (
                    stock_code,
                    snapshot_date,
                    stock_name,
                    _json_text(r.get("raw_payload") or r),
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def log_data_job(
        self,
        job_name: str,
        trade_date: str | None,
        status: str,
        message: str | None = None,
        details: dict[str, Any] | list[Any] | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> int:
        """记录一次采集或派生任务。"""
        self.conn.execute(
            """
            insert into data_jobs(job_name, trade_date, status, message, details, started_at, finished_at)
            values(?, ?, ?, ?, ?, ?, ?)
            """,
            (job_name, trade_date, status, message, _json_text(details) if details is not None else None, started_at, finished_at),
        )
        self.conn.commit()
        return 1

    def _parse_hot_plate(self, item: Any) -> tuple[str, str, float | None] | None:
        if isinstance(item, list) and len(item) >= 2:
            score = item[2] if len(item) >= 3 else None
            return str(item[0]), str(item[1]), score
        if isinstance(item, dict):
            plate_code = item.get("plate_code") or item.get("code")
            plate_name = item.get("plate_name") or item.get("name")
            if plate_code and plate_name:
                return str(plate_name), str(plate_code), item.get("score") or item.get("plate_score")
        return None
