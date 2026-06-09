import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class MarketDbTests(unittest.TestCase):
    def test_schema_has_tables_for_all_known_data_channels(self):
        from db import MarketDB

        expected_tables = {
            "trade_calendar",
            "stocks",
            "plates",
            "raw_api_responses",
            "limit_up_events",
            "limit_up_plate_map",
            "plate_hot_rank",
            "plate_daily",
            "plate_trends",
            "plate_index_daily",
            "plate_reasons",
            "lhb_daily",
            "movement_alerts",
            "market_index_daily",
            "sentiment_daily",
            "market_hot_daily",
            "stock_kline_daily",
            "stock_trends",
            "stock_info_snapshots",
            "market_breadth_daily",
            "limit_down_events",
            "broken_limit_up_events",
            "daily_reviews",
            "data_jobs",
        }

        with tempfile.TemporaryDirectory() as tmp:
            db = MarketDB(Path(tmp) / "market.db")
            db.init_schema()
            tables = {
                row[0]
                for row in db.conn.execute(
                    "select name from sqlite_master where type = 'table'"
                ).fetchall()
            }
            db.close()

        self.assertTrue(expected_tables.issubset(tables))

    def test_data_jobs_upgrade_and_latest_query(self):
        from db import MarketDB
        from server.services.review_queries import get_latest_data_job

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.log_data_job(
                "daily_update",
                "2026-06-05",
                "success",
                "ok",
                details={"steps": [{"name": "生成复盘", "status": "success"}]},
                started_at="2026-06-05T17:30:00",
                finished_at="2026-06-05T17:40:00",
            )
            db.close()

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                job = get_latest_data_job(conn, "daily_update")
            finally:
                conn.close()

        self.assertIsNotNone(job)
        self.assertEqual("success", job["status"])
        self.assertEqual("2026-06-05", job["trade_date"])
        self.assertEqual("生成复盘", job["details"]["steps"][0]["name"])

    def test_scheduler_next_run_time_rolls_to_tomorrow_after_run_time(self):
        from daily_scheduler import next_run_time

        before = datetime(2026, 6, 8, 17, 0)
        after = datetime(2026, 6, 8, 18, 0)

        self.assertEqual(datetime(2026, 6, 8, 17, 30), next_run_time("17:30", before))
        self.assertEqual(datetime(2026, 6, 9, 17, 30), next_run_time("17:30", after))

    def test_daily_update_records_missing_token_failure(self):
        import daily_update
        from server.services.review_queries import get_latest_data_job

        original_load_token = daily_update.load_token
        daily_update.load_token = lambda: None
        try:
            with tempfile.TemporaryDirectory() as tmp:
                db_path = Path(tmp) / "market.db"
                summary = daily_update.run_daily_update(
                    trade_date="2026-06-05",
                    db_path=str(db_path),
                    kline_limit=0,
                    force=True,
                )

                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                try:
                    job = get_latest_data_job(conn, "daily_update")
                finally:
                    conn.close()
        finally:
            daily_update.load_token = original_load_token

        self.assertEqual("failed", summary["status"])
        self.assertIsNotNone(job)
        self.assertEqual("failed", job["status"])
        self.assertIn("未找到 token", job["message"])

    def test_import_plate_index_daily_keeps_real_board_ohlc(self):
        from db import MarketDB

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            count = db.import_plate_index_daily([
                {
                    "plate_code": "801159",
                    "plate_name": "机器人概念",
                    "board_type": "concept",
                    "source": "ths_concept_index",
                    "trade_date": "2026-06-04",
                    "open_price": 4153.07,
                    "high_price": 4185.678,
                    "low_price": 4134.25,
                    "close_price": 4159.71,
                    "change_pct": -0.67,
                    "volume": 31458318000,
                    "amount": 825457400000,
                    "raw_payload": {"matched_name": "机器人概念"},
                },
                {
                    "plate_code": "801159",
                    "plate_name": "机器人概念",
                    "board_type": "concept",
                    "source": "ths_concept_index",
                    "trade_date": "2026-06-05",
                    "open_price": 4149.977,
                    "high_price": 4271.662,
                    "low_price": 4089.864,
                    "close_price": 4202.37,
                    "change_pct": 1.03,
                    "volume": 38270035000,
                    "amount": 946660100000,
                    "raw_payload": {"matched_name": "机器人概念"},
                },
            ])
            db.close()

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select plate_name, board_type, source, close_price, change_pct, amount, raw_payload
                from plate_index_daily
                where plate_code = '801159' and trade_date = '2026-06-05'
                """
            ).fetchone()
            conn.close()

        self.assertEqual(2, count)
        self.assertEqual("机器人概念", row["plate_name"])
        self.assertEqual("concept", row["board_type"])
        self.assertEqual("ths_concept_index", row["source"])
        self.assertEqual(4202.37, row["close_price"])
        self.assertEqual(1.03, row["change_pct"])
        self.assertIn("机器人概念", row["raw_payload"])

    def test_resolve_ths_symbol_matches_common_local_plate_names(self):
        from fetch_plate_index_daily import resolve_ths_symbol

        concept_names = {"芯片概念", "股权转让(并购重组)", "2026一季报预增", "机器人概念"}
        industry_names = {"半导体"}

        self.assertEqual(("concept", "芯片概念"), resolve_ths_symbol("芯片", concept_names, industry_names))
        self.assertEqual(("concept", "股权转让(并购重组)"), resolve_ths_symbol("股权转让", concept_names, industry_names))
        self.assertEqual(("concept", "2026一季报预增"), resolve_ths_symbol("一季报增长", concept_names, industry_names))
        self.assertEqual(("concept", "机器人概念"), resolve_ths_symbol("机器人概念", concept_names, industry_names))

    def test_resolve_ths_symbol_uses_unique_clean_name_match(self):
        from fetch_plate_index_daily import resolve_ths_symbol

        concept_names = {"金属新材料", "汽车芯片", "汽车零部件"}
        industry_names = {"房地产"}

        self.assertEqual(("concept", "金属新材料"), resolve_ths_symbol("新材料概念", concept_names, industry_names))
        self.assertEqual(("industry", "房地产"), resolve_ths_symbol("地产链", concept_names, industry_names))
        self.assertIsNone(resolve_ths_symbol("汽车类", concept_names, industry_names))

    def test_recent_core_plates_include_recent_hot_rank_plates(self):
        from db import MarketDB
        from fetch_plate_index_daily import get_recent_core_plates

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day({
                "date": "2026-06-05",
                "uplimit_reason": [
                    {
                        "plate_code": "809999",
                        "plate_name": "杂项",
                        "stocks": [{"stock_code": "600001", "stock_name": "杂项股"}],
                    }
                ],
                "uplimit_hot": [["芯片", "801001", 5460], ["杂项", "809999", 100]],
                "plate_rank": [],
            }, raw_source="unit-test")
            db.close()

            plates = get_recent_core_plates(db_path, end_date="2026-06-05", review_days=1, per_day_limit=2)

        self.assertTrue(any(plate["plate_code"] == "801001" for plate in plates))

    def test_import_uplimit_day_deduplicates_stocks_and_keeps_plate_links(self):
        from db import MarketDB

        sample = {
            "date": "2026-06-01",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "plate_score": 100,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "stock_price": 14.0,
                            "up_limit_desc": "3连板",
                            "up_limit_time": "09:30",
                            "up_limit_type": "一",
                            "reason": "芯片原因",
                            "fengdan_money": 94192000.0,
                            "turnover_ration_real": 2.86,
                            "actualcirculation_value": 1966160000.0,
                        }
                    ],
                },
                {
                    "plate_code": "801002",
                    "plate_name": "并购重组",
                    "plate_score": 80,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "stock_price": 14.0,
                            "up_limit_desc": "3连板",
                            "up_limit_time": "09:30",
                            "up_limit_type": "一",
                            "reason": "并购重组原因",
                        }
                    ],
                },
            ],
            "uplimit_hot": [["芯片", "801001", 100]],
            "plate_rank": [{"plate_code": "801001", "plate_name": "芯片", "rank": 1}],
        }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day(sample, raw_source="unit-test")
            db.import_uplimit_day(sample, raw_source="unit-test")
            db.close()

            conn = sqlite3.connect(db_path)
            self.assertEqual(1, conn.execute("select count(*) from limit_up_events").fetchone()[0])
            self.assertEqual(2, conn.execute("select count(*) from limit_up_plate_map").fetchone()[0])
            self.assertEqual(2, conn.execute("select count(*) from plates").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from stocks").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from plate_hot_rank").fetchone()[0])
            conn.close()

    def test_migrate_uplimit_jsons_imports_daily_files_only(self):
        from db import MarketDB
        from migrate_json_to_db import migrate_uplimit_jsons

        day = {
            "date": "2026-06-01",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "stocks": [{"stock_code": "002918", "stock_name": "蒙娜丽莎"}],
                }
            ],
            "uplimit_hot": [],
            "plate_rank": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "uplimit_2026-06-01.json").write_text(
                __import__("json").dumps(day, ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "summary_15d.json").write_text("{}", encoding="utf-8")

            db_path = root / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            imported = migrate_uplimit_jsons(root, db)
            db.close()

            self.assertEqual(["2026-06-01"], imported)
            conn = sqlite3.connect(db_path)
            self.assertEqual(1, conn.execute("select count(*) from limit_up_events").fetchone()[0])
            conn.close()

    def test_fetch_uplimit_data_writes_to_database(self):
        from db import MarketDB
        from fetch_uplimit import fetch_uplimit_data

        class FakeAPI:
            def get_uplimit_reason(self, date, page_size=200):
                return {
                    "code": 20000,
                    "data": [
                        {
                            "plate_code": "801001",
                            "plate_name": "芯片",
                            "stocks": [{"stock_code": "002918", "stock_name": "蒙娜丽莎"}],
                        }
                    ],
                }

            def get_uplimit_hot(self, date, limit=20):
                return {"code": 20000, "data": {"plate": [["芯片", "801001", 100]]}}

            def get_plate_rank(self, date, limit=30):
                return {"code": 20000, "data": [{"plate_code": "801001", "plate_name": "芯片"}]}

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            fetch_uplimit_data(FakeAPI(), "2026-06-01", db=db)
            db.close()

            conn = sqlite3.connect(db_path)
            self.assertEqual(1, conn.execute("select count(*) from limit_up_events").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from plate_hot_rank").fetchone()[0])
            conn.close()

    def test_fetch_uplimit_data_still_writes_when_plate_rank_fails(self):
        from db import MarketDB
        from fetch_uplimit import fetch_uplimit_data

        class FakeAPI:
            def get_uplimit_reason(self, date, page_size=200):
                return {
                    "code": 20000,
                    "data": [
                        {
                            "plate_code": "801001",
                            "plate_name": "芯片",
                            "stocks": [{"stock_code": "002918", "stock_name": "蒙娜丽莎"}],
                        }
                    ],
                }

            def get_uplimit_hot(self, date, limit=20):
                return {"code": 20000, "data": {"plate": [["芯片", "801001", 100]]}}

            def get_plate_rank(self, date, limit=30):
                raise RuntimeError("unauthorized")

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            fetch_uplimit_data(FakeAPI(), "2026-06-05", db=db)
            db.close()

            conn = sqlite3.connect(db_path)
            self.assertEqual(1, conn.execute("select count(*) from limit_up_events").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from plate_hot_rank").fetchone()[0])
            conn.close()

    def test_build_html_preview_contains_market_sections(self):
        from db import MarketDB
        from build_data_preview_html import build_html_preview

        sample = {
            "date": "2026-06-01",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "plate_score": 100,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "stock_price": 14.0,
                            "up_limit_desc": "3连板",
                            "up_limit_time": "09:30",
                            "reason": "芯片原因",
                        }
                    ],
                }
            ],
            "uplimit_hot": [["芯片", "801001", 100]],
            "plate_rank": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            db = MarketDB(Path(tmp) / "market.db")
            db.init_schema()
            db.import_uplimit_day(sample, raw_source="unit-test")
            html = build_html_preview(db.db_path, "2026-06-01")
            db.close()

        self.assertIn("2026-06-01", html)
        self.assertIn("去重后涨停股", html)
        self.assertIn("热门板块", html)
        self.assertIn("蒙娜丽莎", html)
        self.assertIn("芯片", html)

    def test_data_server_renders_database_backed_request(self):
        from db import MarketDB
        from data_server import render_path

        sample = {
            "date": "2026-06-01",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "stocks": [{"stock_code": "002918", "stock_name": "蒙娜丽莎"}],
                }
            ],
            "uplimit_hot": [["芯片", "801001", 100]],
            "plate_rank": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            db = MarketDB(Path(tmp) / "market.db")
            db.init_schema()
            db.import_uplimit_day(sample, raw_source="unit-test")
            db.close()

            status, content_type, body = render_path("/?date=2026-06-01", Path(tmp) / "market.db")

        self.assertEqual(200, status)
        self.assertEqual("text/html; charset=utf-8", content_type)
        self.assertIn("市场数据预览", body)
        self.assertIn("蒙娜丽莎", body)
        self.assertIn("2026-06-01", body)

    def test_import_market_breadth_keeps_daily_snapshot(self):
        from db import MarketDB

        snapshot = {
            "trade_date": "2026-06-03",
            "total_count": 5300,
            "up_count": 3100,
            "down_count": 1900,
            "flat_count": 300,
            "limit_up_count": 90,
            "limit_down_count": 11,
            "natural_limit_up_count": 86,
            "natural_limit_down_count": 9,
            "avg_change_pct": -0.37,
            "amount": 1_200_000_000_000,
        }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            self.assertEqual(1, db.import_market_breadth("2026-06-03", snapshot))
            self.assertEqual(1, db.import_market_breadth("2026-06-03", {**snapshot, "up_count": 3200}))
            self.assertEqual(1, db.import_market_breadth("2026-06-03", {"amount": 1_500_000_000_000}))
            db.close()

            conn = sqlite3.connect(db_path)
            row = conn.execute(
                """
                select count(*), up_count, amount, natural_limit_up_count,
                       natural_limit_down_count, avg_change_pct
                from market_breadth_daily
                where trade_date = '2026-06-03'
                """
            ).fetchone()
            self.assertEqual((1, 3200, 1_500_000_000_000, 86, 9, -0.37), row)
            conn.close()

    def test_import_hot_stocks_keeps_amount_source_and_raw_payload(self):
        from db import MarketDB

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            self.assertEqual(1, db.import_hot_stocks("2026-06-05", [{
                "rank_no": 1,
                "stock_code": "300308",
                "stock_name": "中际旭创",
                "latest_price": 179.99,
                "change_pct": -7.81,
                "change_amount": -15.26,
                "amount": 12_300_000_000,
                "turnover_rate": 6.2,
                "source": "eastmoney_hot_rank",
                "raw_payload": {"rank_change": -1},
            }]))
            db.close()

            conn = sqlite3.connect(db_path)
            row = conn.execute(
                """
                select amount, turnover_rate, source, raw_payload
                from hot_stocks
                where trade_date = '2026-06-05' and stock_code = '300308'
                """
            ).fetchone()
            conn.close()

        self.assertEqual(12_300_000_000, row[0])
        self.assertEqual(6.2, row[1])
        self.assertEqual("eastmoney_hot_rank", row[2])
        self.assertIn('"rank_change": -1', row[3])

    def test_market_overview_trend_returns_recent_totals(self):
        from db import MarketDB
        from server.services.review_queries import get_market_overview_trend

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            for i, trade_date in enumerate(["2026-06-01", "2026-06-02", "2026-06-03"], start=1):
                db.import_uplimit_day({
                    "date": trade_date,
                    "uplimit_reason": [
                        {
                            "plate_code": "801001",
                            "plate_name": "芯片",
                            "stocks": [
                                {
                                    "stock_code": f"00000{i}",
                                    "stock_name": f"样本{i}",
                                    "up_limit_keep_times": i,
                                    "up_limit_desc": "首板" if i == 1 else f"{i}连板",
                                }
                            ],
                        }
                    ],
                    "uplimit_hot": [],
                    "plate_rank": [],
                })
                db.import_market_breadth(trade_date, {
                    "total_count": 5000,
                    "up_count": 2000 + i * 100,
                    "down_count": 2800 - i * 100,
                    "flat_count": 200,
                    "limit_up_count": i,
                    "limit_down_count": i + 1,
                    "amount": 1_000_000_000_000 + i * 100_000_000_000,
                })
                db.import_broken_limit_up_events(trade_date, [
                    {"stock_code": f"60{i:04d}", "stock_name": f"炸板{i}", "open_count": i}
                ])
            trend = get_market_overview_trend(db.conn, "2026-06-03", days=2)
            db.close()

        self.assertEqual(["2026-06-02", "2026-06-03"], [item["date"] for item in trend])
        self.assertEqual(1_300_000_000_000, trend[-1]["amount"])
        self.assertEqual(46.0, trend[-1]["up_rate"])
        self.assertEqual(3, trend[-1]["limit_up_count"])
        self.assertEqual(4, trend[-1]["limit_down_count"])
        self.assertEqual(1, trend[-1]["broken_limit_up_count"])
        self.assertEqual(3, trend[-1]["highest_board"])
        self.assertEqual(round((1_300_000_000_000 - 1_200_000_000_000) / 1_200_000_000_000 * 100, 2), trend[-1]["amount_change_pct"])

    def test_market_overview_trend_includes_amount_only_dates(self):
        from db import MarketDB
        from server.services.review_queries import get_market_overview_trend

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_market_breadth("2026-06-01", {"amount": 1_000_000_000_000})
            db.import_market_breadth("2026-06-02", {"amount": 1_200_000_000_000})
            db.import_uplimit_day({
                "date": "2026-06-03",
                "uplimit_reason": [
                    {
                        "plate_code": "801001",
                        "plate_name": "芯片",
                        "stocks": [{"stock_code": "000001", "stock_name": "样本"}],
                    }
                ],
                "uplimit_hot": [],
                "plate_rank": [],
            })
            db.import_market_breadth("2026-06-03", {"amount": 1_500_000_000_000})
            trend = get_market_overview_trend(db.conn, "2026-06-03", days=3)
            db.close()

        self.assertEqual(["2026-06-01", "2026-06-02", "2026-06-03"], [item["date"] for item in trend])
        self.assertEqual(1_200_000_000_000, trend[1]["amount"])
        self.assertEqual(20.0, trend[1]["amount_change_pct"])
        self.assertFalse(trend[0]["has_limit_up_events"])
        self.assertTrue(trend[-1]["has_limit_up_events"])

    def test_emotion_heat_trend_derived_from_daily_sources(self):
        from db import MarketDB
        from server.services.review_queries import get_emotion_heat_trend

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day({
                "date": "2026-06-05",
                "uplimit_reason": [
                    {
                        "plate_code": "801001",
                        "plate_name": "算力",
                        "stocks": [
                            {
                                "stock_code": "300308",
                                "stock_name": "中际旭创",
                                "up_limit_desc": "3连板",
                                "up_limit_keep_times": 3,
                                "up_limit_time": "09:31",
                                "fengdan_money": 90_000_000,
                                "fengdan_rate": 2.5,
                            },
                            {
                                "stock_code": "000725",
                                "stock_name": "京东方A",
                                "up_limit_desc": "首板",
                                "up_limit_keep_times": 1,
                                "up_limit_time": "10:02",
                                "fengdan_money": 20_000_000,
                                "fengdan_rate": 1.2,
                            },
                            {
                                "stock_code": "002222",
                                "stock_name": "样本科技",
                                "up_limit_desc": "2连板",
                                "up_limit_keep_times": 2,
                                "up_limit_time": "13:14",
                                "fengdan_money": 10_000_000,
                                "fengdan_rate": 0.8,
                            },
                        ],
                    }
                ],
                "uplimit_hot": [],
                "plate_rank": [],
            })
            db.import_market_breadth("2026-06-05", {
                "total_count": 5300,
                "up_count": 2400,
                "down_count": 2800,
                "flat_count": 100,
                "limit_up_count": 3,
                "limit_down_count": 1,
                "natural_limit_up_count": 55,
                "natural_limit_down_count": 10,
                "avg_change_pct": -0.37,
                "amount": 1_200_000_000_000,
            })
            db.import_limit_down_events("2026-06-05", [
                {"stock_code": "600001", "stock_name": "跌停样本", "change_pct": -10.0}
            ])
            db.import_broken_limit_up_events("2026-06-05", [
                {"stock_code": "600696", "stock_name": "炸板样本", "open_count": 2}
            ])
            db.import_hot_stocks("2026-06-05", [
                {"rank_no": 1, "stock_code": "300308", "stock_name": "中际旭创", "change_pct": 10.0},
                {"rank_no": 2, "stock_code": "000725", "stock_name": "京东方A", "change_pct": -1.0},
                {"rank_no": 3, "stock_code": "300001", "stock_name": "非涨停强股", "change_pct": 4.0},
                {"rank_no": 4, "stock_code": "600001", "stock_name": "跌停样本", "change_pct": -6.0},
            ])

            trend = get_emotion_heat_trend(db.conn, "2026-06-05", days=1)
            db.close()

        self.assertEqual(1, len(trend))
        item = trend[0]
        self.assertEqual("2026-06-05", item["date"])
        self.assertEqual(-0.37, item["avg_change_pct"])
        self.assertEqual(55, item["natural_limit_up_count"])
        self.assertEqual(75.0, item["seal_success_rate"])
        self.assertEqual(25.0, item["broken_rate"])
        self.assertEqual(1.75, item["hot_top20_avg_change_pct"])
        self.assertEqual(2, item["hot_top20_up_count"])
        self.assertEqual(2, item["hot_top20_down_count"])
        self.assertEqual(1, item["hot_top20_heavy_fall_count"])
        self.assertEqual(2, item["hot_limit_up_overlap_count"])
        self.assertEqual(50.0, item["hot_limit_up_overlap_rate"])
        self.assertEqual(3, item["highest_board"])
        self.assertEqual("中际旭创", item["space_board_stocks"][0]["stock_name"])

    def test_emotion_heat_trend_caps_hot_rank_to_twenty_rows(self):
        from db import MarketDB
        from server.services.review_queries import get_emotion_heat_trend

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_market_breadth("2026-06-05", {"amount": 1_200_000_000_000})
            db.import_hot_stocks("2026-06-05", [
                {
                    "rank_no": rank_no,
                    "stock_code": f"300{idx:03d}",
                    "stock_name": f"人气{idx}",
                    "change_pct": 1.0,
                }
                for idx, rank_no in enumerate([1, *range(2, 21), 20, 20, 20], start=1)
            ])

            trend = get_emotion_heat_trend(db.conn, "2026-06-05", days=1)
            db.close()

        self.assertEqual(20, trend[0]["hot_top20_count"])
        self.assertEqual(20, len(trend[0]["hot_top20"]))

    def test_hot_rank_prefers_eastmoney_popularity_over_turnover_rank(self):
        from db import MarketDB
        from server.services.review_queries import get_emotion_heat_trend, get_hot_stocks_rank

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_market_breadth("2026-06-05", {"amount": 1_200_000_000_000})
            db.import_hot_stocks("2026-06-05", [
                {
                    "rank_no": 1,
                    "stock_code": "300001",
                    "stock_name": "成交额榜一",
                    "change_pct": 9.0,
                    "source": "spot_amount_rank",
                },
                {
                    "rank_no": 1,
                    "stock_code": "600001",
                    "stock_name": "人气榜一",
                    "change_pct": 2.0,
                    "source": "eastmoney_emappdata",
                },
                {
                    "rank_no": 2,
                    "stock_code": "600002",
                    "stock_name": "人气榜二",
                    "change_pct": -1.0,
                    "source": "eastmoney_emappdata",
                },
            ])

            hot_rank = get_hot_stocks_rank(db.conn, "2026-06-05", limit=10)
            trend = get_emotion_heat_trend(db.conn, "2026-06-05", days=1)
            db.close()

        self.assertEqual(["人气榜一", "人气榜二"], [item["stock_name"] for item in hot_rank])
        self.assertEqual(2, trend[0]["hot_top20_count"])
        self.assertEqual(0.5, trend[0]["hot_top20_avg_change_pct"])
        self.assertEqual(["人气榜一", "人气榜二"], [item["stock_name"] for item in trend[0]["hot_top20"]])

    def test_quantzz_daily_overview_combines_daily_review_modules(self):
        from db import MarketDB
        from server.services.review_queries import get_quantzz_daily_overview

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day({
                "date": "2026-06-04",
                "uplimit_reason": [
                    {
                        "plate_code": "801001",
                        "plate_name": "算力",
                        "plate_score": 80,
                        "stocks": [
                            {
                                "stock_code": "600001",
                                "stock_name": "晋级样本",
                                "up_limit_desc": "2连板",
                                "up_limit_keep_times": 2,
                            },
                            {
                                "stock_code": "600002",
                                "stock_name": "断板样本",
                                "up_limit_desc": "2连板",
                                "up_limit_keep_times": 2,
                            },
                        ],
                    }
                ],
                "uplimit_hot": [["算力", "801001", 80]],
                "plate_rank": [],
            })
            db.import_uplimit_day({
                "date": "2026-06-05",
                "uplimit_reason": [
                    {
                        "plate_code": "801001",
                        "plate_name": "算力",
                        "plate_score": 100,
                        "stocks": [
                            {
                                "stock_code": "600001",
                                "stock_name": "晋级样本",
                                "up_limit_desc": "3连板",
                                "up_limit_keep_times": 3,
                                "up_limit_time": "09:31",
                                "fengdan_money": 90_000_000,
                                "fengdan_rate": 2.0,
                            },
                            {
                                "stock_code": "300001",
                                "stock_name": "首板样本",
                                "up_limit_desc": "首板",
                                "up_limit_keep_times": 1,
                                "up_limit_time": "10:10",
                                "fengdan_money": 20_000_000,
                                "fengdan_rate": 0.8,
                            },
                        ],
                    }
                ],
                "uplimit_hot": [["算力", "801001", 100]],
                "plate_rank": [],
            })
            db.import_market_breadth("2026-06-05", {
                "total_count": 5300,
                "up_count": 2400,
                "down_count": 2800,
                "flat_count": 100,
                "limit_up_count": 2,
                "limit_down_count": 8,
                "natural_limit_up_count": 66,
                "natural_limit_down_count": 12,
                "avg_change_pct": -0.42,
                "amount": 1_500_000_000_000,
            })
            db.import_limit_down_events("2026-06-05", [
                {"stock_code": "000001", "stock_name": "跌停样本", "change_pct": -10.0}
            ])
            db.import_broken_limit_up_events("2026-06-05", [
                {"stock_code": "000002", "stock_name": "炸板样本", "change_pct": -3.0}
            ])
            db.import_hot_stocks("2026-06-05", [
                {"rank_no": 1, "stock_code": "600001", "stock_name": "晋级样本", "change_pct": 10.0, "source": "eastmoney_emappdata"},
                {"rank_no": 2, "stock_code": "000725", "stock_name": "人气趋势", "change_pct": -6.0, "source": "eastmoney_emappdata"},
                {"rank_no": 1, "stock_code": "300999", "stock_name": "成交额榜", "change_pct": 8.0, "source": "spot_amount_rank"},
            ])
            db.import_hot_boards("2026-06-05", [
                {"rank_no": 1, "board_code": "801001", "board_name": "算力", "change_pct": 3.2, "up_count": 20, "down_count": 8, "leading_stock": "晋级样本"},
            ], "concept")

            overview = get_quantzz_daily_overview(db.conn, "2026-06-05", days=5)
            db.close()

        self.assertEqual("2026-06-05", overview["date"])
        self.assertEqual(3, overview["space_board"]["highest_board"])
        self.assertEqual("晋级样本", overview["space_board"]["stocks"][0]["stock_name"])
        self.assertEqual(2, overview["popularity"]["top20_count"])
        self.assertEqual(["晋级样本", "人气趋势"], [item["stock_name"] for item in overview["popularity"]["top20"]])
        self.assertEqual(1, overview["popularity"]["limit_up_overlap_count"])
        self.assertEqual("算力", overview["hot_boards"]["concept"][0]["board_name"])
        self.assertEqual(2, overview["promotion"]["levels"][0]["total"])
        self.assertEqual(1, overview["promotion"]["levels"][0]["advanced"])
        self.assertEqual(1, overview["promotion"]["levels"][0]["failed"])
        self.assertEqual(1, overview["loss_feedback"]["limit_down_count"])
        self.assertEqual(1, overview["loss_feedback"]["broken_limit_up_count"])
        self.assertTrue(any(item["key"] == "auction" for item in overview["missing_sources"]))

    def test_import_limit_down_and_broken_boards_deduplicates_by_date_and_code(self):
        from db import MarketDB

        limit_down = [
            {
                "stock_code": "003030",
                "stock_name": "祖名股份",
                "latest_price": 21.47,
                "change_pct": -9.98,
                "amount": 154983774,
                "limit_down_days": 1,
                "open_count": 6,
                "industry": "农产品加工",
            }
        ]
        broken = [
            {
                "stock_code": "600696",
                "stock_name": "退市岩石",
                "latest_price": 0.63,
                "change_pct": 3.28,
                "first_limit_up_time": "09:25:02",
                "open_count": 1,
                "limit_up_stat": "2/1",
                "industry": "白酒",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            self.assertEqual(1, db.import_limit_down_events("2026-06-03", limit_down))
            self.assertEqual(1, db.import_limit_down_events("2026-06-03", limit_down))
            self.assertEqual(1, db.import_broken_limit_up_events("2026-06-03", broken))
            self.assertEqual(1, db.import_broken_limit_up_events("2026-06-03", broken))
            db.close()

            conn = sqlite3.connect(db_path)
            self.assertEqual(1, conn.execute("select count(*) from limit_down_events").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from broken_limit_up_events").fetchone()[0])
            conn.close()

    def test_import_lhb_market_hot_movement_and_kline(self):
        from db import MarketDB

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            self.assertEqual(1, db.import_lhb_daily("2026-06-03", [{
                "stock_code": "000539",
                "stock_name": "粤电力A",
                "reason": "日振幅值达到15%的前5只证券",
                "buy_amount": 374078893.7,
                "sell_amount": 628527020.82,
                "net_buy_amount": -254448127.12,
            }]))
            self.assertEqual(1, db.import_market_hot_daily("2026-06-03", [{
                "item_key": "AI应用",
                "item_name": "AI应用",
                "score": 498,
                "rank_no": 1,
            }]))
            self.assertEqual(1, db.import_movement_alerts("2026-06-03", [{
                "alert_time": "14:30:00",
                "stock_code": "002918",
                "stock_name": "蒙娜丽莎",
                "alert_type": "尾盘拉升",
                "alert_text": "尾盘快速拉升",
                "price": 14.0,
                "change_pct": 5.2,
            }]))
            self.assertEqual(1, db.import_stock_kline_daily("002918", [{
                "trade_date": "2026-06-03",
                "open_price": 13.0,
                "high_price": 14.0,
                "low_price": 12.8,
                "close_price": 14.0,
                "volume": 10000,
                "amount": 14000000,
            }]))
            self.assertEqual(1, db.import_index_daily("2026-06-03", [{
                "code": "000001.SS",
                "name": "上证指数",
                "last_px": 4083.97,
                "px_change_rate": 0.22,
                "amount": 66000000000,
                "raw": {"date": date(2026, 6, 3)},
            }]))
            db.close()

            conn = sqlite3.connect(db_path)
            self.assertEqual(1, conn.execute("select count(*) from lhb_daily").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from market_hot_daily").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from movement_alerts").fetchone()[0])
            self.assertEqual(1, conn.execute("select count(*) from stock_kline_daily").fetchone()[0])
            row = conn.execute(
                "select index_name, close_price, change_pct, amount from market_index_daily where index_code = '000001.SS'"
            ).fetchone()
            self.assertEqual(("上证指数", 4083.97, 0.22, 66000000000), row)
            conn.close()

    def test_market_environment_reports_totals_separately_from_preview_lists(self):
        from db import MarketDB
        from server.services.review_queries import get_market_environment

        with tempfile.TemporaryDirectory() as tmp:
            db = MarketDB(Path(tmp) / "market.db")
            db.init_schema()
            db.import_uplimit_day({
                "date": "2026-06-05",
                "uplimit_reason": [
                    {
                        "plate_code": "801001",
                        "plate_name": "芯片",
                        "stocks": [{"stock_code": "002918", "stock_name": "蒙娜丽莎"}],
                    }
                ],
                "uplimit_hot": [],
                "plate_rank": [],
            })
            db.import_market_breadth("2026-06-05", {
                "total_count": 5000,
                "up_count": 2500,
                "down_count": 2400,
                "flat_count": 100,
                "limit_up_count": 1,
                "limit_down_count": 0,
                "amount": 1_000_000_000_000,
            })
            db.import_limit_down_events("2026-06-05", [
                {
                    "stock_code": f"00{i:04d}",
                    "stock_name": f"跌停{i}",
                    "change_pct": -10,
                    "amount": i,
                }
                for i in range(25)
            ])
            db.import_broken_limit_up_events("2026-06-05", [
                {
                    "stock_code": f"60{i:04d}",
                    "stock_name": f"炸板{i}",
                    "change_pct": 5,
                    "amount": i,
                    "open_count": i % 5,
                }
                for i in range(30)
            ])

            result = get_market_environment(db.conn, "2026-06-05")
            db.close()

        self.assertEqual(25, result["limit_down_total"])
        self.assertEqual(30, result["broken_limit_up_total"])
        self.assertEqual(20, len(result["limit_down"]))
        self.assertEqual(20, len(result["broken_limit_up"]))
        self.assertEqual(25, result["breadth"]["limit_down_count"])

    def test_generate_daily_review_saves_structured_report_and_markdown(self):
        from db import MarketDB
        from generate_review import generate_daily_review
        from server.services.review_queries import get_saved_review

        sample = {
            "date": "2026-06-05",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "plate_score": 100,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "up_limit_desc": "3连板",
                            "up_limit_keep_times": 3,
                            "up_limit_time": "09:31",
                            "fengdan_money": 90_000_000,
                            "reason": "芯片景气",
                        },
                        {
                            "stock_code": "300001",
                            "stock_name": "特锐德",
                            "up_limit_desc": "首板",
                            "up_limit_keep_times": 1,
                            "up_limit_time": "10:01",
                            "fengdan_money": 50_000_000,
                            "reason": "充电桩",
                        },
                    ],
                },
                {
                    "plate_code": "801002",
                    "plate_name": "机器人",
                    "plate_score": 80,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "up_limit_desc": "3连板",
                            "up_limit_keep_times": 3,
                            "up_limit_time": "09:31",
                            "fengdan_money": 90_000_000,
                            "reason": "机器人叠加",
                        },
                        {
                            "stock_code": "600001",
                            "stock_name": "机器人A",
                            "up_limit_desc": "2连板",
                            "up_limit_keep_times": 2,
                            "up_limit_time": "09:45",
                            "fengdan_money": 60_000_000,
                            "reason": "机器人催化",
                        },
                    ],
                },
            ],
            "uplimit_hot": [["芯片", "801001", 100], ["机器人", "801002", 80]],
            "plate_rank": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            out_dir = Path(tmp) / "reports"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day(sample, raw_source="unit-test")
            db.import_market_breadth("2026-06-05", {
                "total_count": 5000,
                "up_count": 2600,
                "down_count": 2200,
                "flat_count": 200,
                "limit_up_count": 3,
                "limit_down_count": 2,
                "amount": 1_100_000_000_000,
            })
            db.import_broken_limit_up_events("2026-06-05", [
                {"stock_code": f"60{i:04d}", "stock_name": f"炸板{i}", "open_count": 2}
                for i in range(8)
            ])
            db.close()

            review = generate_daily_review("2026-06-05", db_path=db_path, output_dir=out_dir)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            saved = get_saved_review(conn, "2026-06-05")
            conn.close()

            self.assertEqual("2026-06-05", review["trade_date"])
            self.assertIn("芯片", review["summary"])
            self.assertTrue(review["risk_flags"])
            self.assertTrue(review["next_plan"])
            self.assertEqual(3, review["limit_up_stock_count"])
            self.assertEqual(1, review["first_board_count"])
            self.assertEqual(2, review["multi_board_count"])
            self.assertEqual("芯片", review["strongest_plates"][0]["plate_name"])
            self.assertEqual("蒙娜丽莎", review["core_stocks"][0]["stock_name"])
            self.assertIsNotNone(saved)
            self.assertEqual("2026-06-05", saved["trade_date"])
            self.assertEqual(1, saved["first_board_count"])
            self.assertEqual(2, saved["multi_board_count"])
            self.assertIn("芯片", saved["summary"])
            self.assertTrue(Path(saved["markdown_path"]).exists())
            self.assertIn("# A股复盘 2026-06-05", Path(saved["markdown_path"]).read_text(encoding="utf-8"))

    def test_generate_daily_review_includes_non_limit_up_hot_stocks(self):
        from db import MarketDB
        from generate_review import generate_daily_review
        from server.services.review_queries import get_saved_review

        sample = {
            "date": "2026-06-05",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "plate_score": 100,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "up_limit_desc": "3连板",
                            "up_limit_keep_times": 3,
                            "up_limit_time": "09:31",
                            "fengdan_money": 90_000_000,
                            "reason": "芯片景气",
                        }
                    ],
                }
            ],
            "uplimit_hot": [["芯片", "801001", 100]],
            "plate_rank": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            out_dir = Path(tmp) / "reports"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day(sample, raw_source="unit-test")
            db.import_hot_stocks("2026-06-05", [
                {
                    "rank_no": 1,
                    "stock_code": "300308",
                    "stock_name": "中际旭创",
                    "latest_price": 81.2,
                    "change_pct": -7.8,
                    "change_amount": -6.9,
                },
                {
                    "rank_no": 2,
                    "stock_code": "000725",
                    "stock_name": "京东方A",
                    "latest_price": 4.6,
                    "change_pct": 4.5,
                    "change_amount": 0.2,
                },
                {
                    "rank_no": 3,
                    "stock_code": "002918",
                    "stock_name": "蒙娜丽莎",
                    "latest_price": 14.0,
                    "change_pct": 10.0,
                    "change_amount": 1.3,
                },
            ])
            db.close()

            review = generate_daily_review("2026-06-05", db_path=db_path, output_dir=out_dir)
            markdown = Path(review["markdown_path"]).read_text(encoding="utf-8")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            saved = get_saved_review(conn, "2026-06-05")
            conn.close()

        self.assertEqual("中际旭创", review["hot_stocks"][0]["stock_name"])
        self.assertFalse(review["hot_stocks"][0]["is_limit_up"])
        self.assertEqual(2, review["hot_stock_summary"]["non_limit_up_count"])
        self.assertTrue(any(stock["stock_name"] == "京东方A" for stock in review["watch_stocks"]))
        self.assertIsNotNone(saved)
        self.assertEqual("中际旭创", saved["hot_stocks"][0]["stock_name"])
        self.assertIn("不是", review["hot_stock_summary"]["text"])
        self.assertIn("明天", review["hot_stock_summary"]["text"])
        self.assertNotIn("说明市场关注点", review["hot_stock_summary"]["text"])
        self.assertIn("风向标", review["watch_stocks"][0]["reason"])
        self.assertIn("趋势股分歧盘", review["summary"])
        self.assertNotIn("非涨停占", review["summary"])
        self.assertIn("人气核心", markdown)
        self.assertIn("非涨停", markdown)
        self.assertIn("中际旭创", review["summary"])

    def test_generate_daily_review_prefers_popularity_rank_over_turnover_rank(self):
        from db import MarketDB
        from generate_review import generate_daily_review

        sample = {
            "date": "2026-06-05",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "算力",
                    "plate_score": 100,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "up_limit_desc": "首板",
                            "up_limit_keep_times": 1,
                            "up_limit_time": "09:31",
                        }
                    ],
                }
            ],
            "uplimit_hot": [],
            "plate_rank": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            out_dir = Path(tmp) / "reports"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day(sample, raw_source="unit-test")
            db.import_hot_stocks("2026-06-05", [
                {
                    "rank_no": 1,
                    "stock_code": "300001",
                    "stock_name": "成交额榜一",
                    "change_pct": 8.0,
                    "source": "spot_amount_rank",
                },
                {
                    "rank_no": 1,
                    "stock_code": "600001",
                    "stock_name": "人气榜一",
                    "change_pct": 2.0,
                    "source": "eastmoney_emappdata",
                },
            ])
            db.close()

            review = generate_daily_review("2026-06-05", db_path=db_path, output_dir=out_dir)

        self.assertEqual("人气榜一", review["hot_stocks"][0]["stock_name"])
        self.assertNotIn("成交额榜一", [stock["stock_name"] for stock in review["hot_stocks"]])

    def test_generate_daily_review_adds_plate_reviews_with_core_stocks(self):
        from db import MarketDB
        from generate_review import generate_daily_review
        from server.services.review_queries import get_saved_review

        def day(trade_date: str, stocks: list[dict]) -> dict:
            return {
                "date": trade_date,
                "uplimit_reason": [
                    {
                        "plate_code": "801001",
                        "plate_name": "芯片",
                        "plate_score": 100,
                        "stocks": stocks,
                    }
                ],
                "uplimit_hot": [["芯片", "801001", 100]],
                "plate_rank": [],
            }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            out_dir = Path(tmp) / "reports"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day(day("2026-06-03", [
                {
                    "stock_code": "002918",
                    "stock_name": "蒙娜丽莎",
                    "up_limit_desc": "首板",
                    "up_limit_keep_times": 1,
                    "up_limit_time": "09:45",
                    "fengdan_money": 20_000_000,
                    "reason": "芯片低位启动",
                }
            ]), raw_source="unit-test")
            db.import_uplimit_day(day("2026-06-04", [
                {
                    "stock_code": "002918",
                    "stock_name": "蒙娜丽莎",
                    "up_limit_desc": "2连板",
                    "up_limit_keep_times": 2,
                    "up_limit_time": "09:38",
                    "fengdan_money": 55_000_000,
                    "reason": "芯片持续发酵",
                },
                {
                    "stock_code": "300001",
                    "stock_name": "特锐德",
                    "up_limit_desc": "首板",
                    "up_limit_keep_times": 1,
                    "up_limit_time": "10:10",
                    "fengdan_money": 18_000_000,
                    "reason": "芯片补涨",
                },
            ]), raw_source="unit-test")
            db.import_uplimit_day(day("2026-06-05", [
                {
                    "stock_code": "002918",
                    "stock_name": "蒙娜丽莎",
                    "up_limit_desc": "3连板",
                    "up_limit_keep_times": 3,
                    "up_limit_time": "09:31",
                    "fengdan_money": 90_000_000,
                    "reason": "芯片景气",
                },
                {
                    "stock_code": "600001",
                    "stock_name": "趋势科技",
                    "up_limit_desc": "首板",
                    "up_limit_keep_times": 1,
                    "up_limit_time": "10:05",
                    "fengdan_money": 30_000_000,
                    "reason": "芯片趋势扩散",
                },
            ]), raw_source="unit-test")
            db.import_hot_stocks("2026-06-05", [
                {
                    "rank_no": 2,
                    "stock_code": "002918",
                    "stock_name": "蒙娜丽莎",
                    "latest_price": 14.0,
                    "change_pct": 10.0,
                    "change_amount": 1.3,
                }
            ])
            db.import_plate_index_daily([
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "board_type": "concept",
                    "source": "ths_concept_index",
                    "trade_date": "2026-06-03",
                    "open_price": 100,
                    "high_price": 103,
                    "low_price": 99,
                    "close_price": 101,
                    "change_pct": None,
                    "volume": 1000,
                    "amount": 10_000,
                },
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "board_type": "concept",
                    "source": "ths_concept_index",
                    "trade_date": "2026-06-04",
                    "open_price": 101,
                    "high_price": 106,
                    "low_price": 100,
                    "close_price": 105,
                    "change_pct": 3.96,
                    "volume": 1200,
                    "amount": 12_000,
                },
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "board_type": "concept",
                    "source": "ths_concept_index",
                    "trade_date": "2026-06-05",
                    "open_price": 105,
                    "high_price": 109,
                    "low_price": 104,
                    "close_price": 108,
                    "change_pct": 2.86,
                    "volume": 1500,
                    "amount": 15_000,
                },
            ])
            db.close()

            review = generate_daily_review("2026-06-05", db_path=db_path, output_dir=out_dir)
            markdown = Path(review["markdown_path"]).read_text(encoding="utf-8")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            saved = get_saved_review(conn, "2026-06-05")
            conn.close()

        self.assertTrue(review["plate_reviews"])
        plate = review["plate_reviews"][0]
        self.assertEqual("芯片", plate["plate_name"])
        self.assertEqual("limit_up_activity", plate["data_scope"])
        self.assertEqual("ths_concept_index", plate["index_summary"]["source"])
        self.assertEqual(2.86, plate["index_summary"]["today_change_pct"])
        self.assertGreater(plate["index_summary"]["window_change_pct"], 0)
        self.assertGreaterEqual(plate["active_days"], 3)
        self.assertIn("真实涨跌", plate["review_text"])
        self.assertNotIn("涨停家数路径", plate["review_text"])
        self.assertIn("近", plate["review_text"])
        self.assertIn("今天", plate["review_text"])
        self.assertTrue(plate["core_stocks"])
        self.assertEqual("蒙娜丽莎", plate["core_stocks"][0]["stock_name"])
        self.assertGreaterEqual(plate["core_stocks"][0]["active_days"], 3)
        self.assertIn("板块核心", plate["core_stocks"][0]["reason"])
        self.assertIsNotNone(saved)
        self.assertEqual("芯片", saved["plate_reviews"][0]["plate_name"])
        self.assertIn("核心板块复盘", markdown)

    def test_derive_review_data_populates_local_summary_tables(self):
        from db import MarketDB
        from derive_review_data import derive_review_data

        day1 = {
            "date": "2026-06-04",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "plate_score": 70,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "up_limit_desc": "2连板",
                            "up_limit_keep_times": 2,
                            "up_limit_time": "09:35",
                            "fengdan_money": 40_000_000,
                            "reason": "芯片老龙反包",
                        }
                    ],
                }
            ],
            "uplimit_hot": [["芯片", "801001", 70]],
            "plate_rank": [],
        }
        day2 = {
            "date": "2026-06-05",
            "uplimit_reason": [
                {
                    "plate_code": "801001",
                    "plate_name": "芯片",
                    "plate_score": 100,
                    "stocks": [
                        {
                            "stock_code": "002918",
                            "stock_name": "蒙娜丽莎",
                            "up_limit_desc": "3连板",
                            "up_limit_keep_times": 3,
                            "up_limit_time": "09:31",
                            "fengdan_money": 90_000_000,
                            "reason": "芯片景气",
                        },
                        {
                            "stock_code": "300001",
                            "stock_name": "特锐德",
                            "up_limit_desc": "首板",
                            "up_limit_keep_times": 1,
                            "up_limit_time": "10:01",
                            "fengdan_money": 50_000_000,
                            "reason": "充电桩叠加芯片",
                        },
                    ],
                }
            ],
            "uplimit_hot": [["芯片", "801001", 100]],
            "plate_rank": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market.db"
            db = MarketDB(db_path)
            db.init_schema()
            db.import_uplimit_day(day1, raw_source="unit-test")
            db.import_uplimit_day(day2, raw_source="unit-test")
            db.import_stock_kline_daily("002918", [
                {
                    "trade_date": "2026-06-05",
                    "open_price": 13.2,
                    "high_price": 14.0,
                    "low_price": 13.0,
                    "close_price": 14.0,
                    "volume": 10000,
                    "amount": 14000000,
                }
            ])
            db.import_daily_review({
                "trade_date": "2026-06-05",
                "limit_up_stock_count": 2,
                "limit_up_plate_count": 1,
                "first_board_count": 1,
                "multi_board_count": 1,
                "highest_board": 3,
                "strongest_plates": [{"plate_code": "801001", "plate_name": "芯片"}],
                "core_stocks": [{"stock_code": "002918", "stock_name": "蒙娜丽莎"}],
                "risk_flags": [],
                "opportunities": [],
                "next_plan": [],
                "summary": "芯片继续走强",
            })
            db.close()

            counts = derive_review_data(db_path)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            trend = conn.execute(
                """
                select close_price, change_pct, amount, raw_payload
                from plate_trends
                where plate_code = '801001' and trade_date = '2026-06-05'
                """
            ).fetchone()
            reason = conn.execute(
                "select reason, raw_payload from plate_reasons where plate_code = '801001'"
            ).fetchone()
            snapshot = conn.execute(
                """
                select stock_name, raw_payload
                from stock_info_snapshots
                where stock_code = '002918' and snapshot_date = '2026-06-05'
                """
            ).fetchone()
            job_count = conn.execute("select count(*) from data_jobs").fetchone()[0]
            conn.close()

        self.assertGreaterEqual(counts["plate_trends"], 2)
        self.assertGreaterEqual(counts["plate_reasons"], 1)
        self.assertGreaterEqual(counts["stock_info_snapshots"], 1)
        self.assertEqual(2, trend["close_price"])
        self.assertEqual(100.0, trend["change_pct"])
        self.assertEqual(140_000_000, trend["amount"])
        self.assertIn("蒙娜丽莎", reason["reason"])
        self.assertIn("芯片景气", reason["raw_payload"])
        self.assertEqual("蒙娜丽莎", snapshot["stock_name"])
        self.assertIn('"close_price": 14.0', snapshot["raw_payload"])
        self.assertGreaterEqual(job_count, 1)

    def test_fetch_hot_resolves_latest_local_trade_day(self):
        from db import MarketDB
        from fetch_hot import resolve_hot_trade_date

        with tempfile.TemporaryDirectory() as tmp:
            db = MarketDB(Path(tmp) / "market.db")
            db.init_schema()
            db.import_uplimit_day({
                "date": "2026-06-05",
                "uplimit_reason": [
                    {
                        "plate_code": "801001",
                        "plate_name": "芯片",
                        "stocks": [{"stock_code": "002918", "stock_name": "蒙娜丽莎"}],
                    }
                ],
                "uplimit_hot": [],
                "plate_rank": [],
            })

            self.assertEqual("2026-06-05", resolve_hot_trade_date(db))
            self.assertEqual("2026-06-03", resolve_hot_trade_date(db, "2026-06-03"))
            db.close()


if __name__ == "__main__":
    unittest.main()
