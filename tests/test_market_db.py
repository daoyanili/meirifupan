import sqlite3
import sys
import tempfile
import unittest
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
            "plate_reasons",
            "lhb_daily",
            "movement_alerts",
            "market_index_daily",
            "sentiment_daily",
            "market_hot_daily",
            "stock_kline_daily",
            "stock_trends",
            "stock_info_snapshots",
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


if __name__ == "__main__":
    unittest.main()
