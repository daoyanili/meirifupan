"""Migrate existing local JSON data into SQLite tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from db import MarketDB


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"
DEFAULT_UPLIMIT_DIR = PROJECT_ROOT / "data" / "uplimit"


def migrate_uplimit_jsons(uplimit_dir: str | Path, db: MarketDB) -> list[str]:
    imported: list[str] = []
    for path in sorted(Path(uplimit_dir).glob("uplimit_*.json")):
        with path.open(encoding="utf-8") as f:
            day_data = json.load(f)
        if "date" not in day_data:
            continue
        db.import_uplimit_day(day_data, raw_source="legacy-json")
        imported.append(day_data["date"])
    return imported


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy uplimit JSON files into SQLite.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--uplimit-dir", default=str(DEFAULT_UPLIMIT_DIR), help="Directory with uplimit_*.json files")
    args = parser.parse_args()

    db = MarketDB(args.db)
    try:
        db.init_schema()
        imported = migrate_uplimit_jsons(args.uplimit_dir, db)
    finally:
        db.close()

    print(f"Imported {len(imported)} trading days into {args.db}")
    if imported:
        print(f"Period: {imported[0]} ~ {imported[-1]}")


if __name__ == "__main__":
    main()
