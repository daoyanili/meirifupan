"""SQLite storage for market review data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


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
            create index if not exists idx_raw_api_responses_endpoint
                on raw_api_responses(endpoint, trade_date);
            create index if not exists idx_movement_alerts_date_time
                on movement_alerts(trade_date, alert_time);
            create index if not exists idx_lhb_daily_date
                on lhb_daily(trade_date);
            create index if not exists idx_stock_kline_daily_date
                on stock_kline_daily(trade_date);
            """
        )
        self.conn.commit()

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
        payload_text = json.dumps(payload, ensure_ascii=False)
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
                    None,
                    json.dumps(idx, ensure_ascii=False),
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
                    json.dumps(item, ensure_ascii=False),
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
