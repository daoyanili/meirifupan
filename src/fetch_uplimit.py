"""爬取近15个交易日的涨停数据"""

import json
import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_client import QuantAPI
from db import MarketDB


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "market_review.db")


def load_token():
    """从浏览器 localStorage 读取 token（需要先登录）"""
    token_file = os.path.join(os.path.dirname(__file__), "..", "config", "token.json")
    if os.path.exists(token_file):
        with open(token_file) as f:
            data = json.load(f)
            return data.get("token")
    return None


def save_token(token: str):
    """保存 token 到文件"""
    token_file = os.path.join(os.path.dirname(__file__), "..", "config", "token.json")
    with open(token_file, "w") as f:
        json.dump({"token": token, "saved_at": datetime.now().isoformat()}, f, indent=2)


def fetch_sentiment_data(api: QuantAPI, db: MarketDB, days: int = 15):
    """Fetch sentiment kline data for recent trading days.

    The sentiment kline API returns OHLC data for the sentiment index.
    We call it with a date from ~20 days ago to ensure we get all 15 trading days,
    then import into sentiment_daily table.
    """
    print(f"\n{'='*50}")
    print(f"Fetching sentiment kline data (period=0, last {days} days)...")
    print(f"{'='*50}")

    # Call with a date from ~20 days ago to get full coverage
    start_date = (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d")
    result = api.get_sentiment_kline(start_date, period=0)

    if result.get("code") != 20000 or not result.get("data"):
        print("  [WARN] No sentiment data returned from API")
        return 0

    kline_data = result["data"]
    print(f"  API returned {len(kline_data)} records")

    # Show date range
    if kline_data:
        first_date = kline_data[0].get("date")
        last_date = kline_data[-1].get("date")
        print(f"  Date range: {first_date} ~ {last_date}")

    # Import into database
    count = db.import_sentiment_daily(kline_data, period=0, raw_source="api")
    print(f"  [OK] Imported {count} sentiment records into sentiment_daily")

    return count


def fetch_uplimit_data(api: QuantAPI, date: str, db: MarketDB):
    """爬取某一天的涨停数据"""
    print(f"\n{'='*50}")
    print(f"爬取 {date} 的涨停数据...")
    print(f"{'='*50}")

    # 1. 涨停原因（含板块、个股详情）
    print("  [1/3] 涨停原因...")
    reason_data = api.get_uplimit_reason(date, page_size=200)
    if reason_data.get("code") == 20000 and reason_data.get("data"):
        plates = reason_data["data"]
        total_stocks = sum(len(p.get("stocks", [])) for p in plates)
        print(f"    ✅ {len(plates)} 个板块, {total_stocks} 只涨停股")
    else:
        plates = []
        print(f"    ⚠️  无数据或接口返回异常")

    # 2. 涨停梯队
    print("  [2/3] 涨停梯队...")
    hot_data = api.get_uplimit_hot(date, limit=20)
    if hot_data.get("code") == 20000 and hot_data.get("data"):
        hot_plates = hot_data["data"].get("plate", [])
        print(f"    ✅ {len(hot_plates)} 个热门板块")
    else:
        hot_plates = []
        print(f"    ⚠️  无数据")

    # 3. 板块排名
    print("  [3/3] 板块排名...")
    rank_data = api.get_plate_rank(date, limit=30)
    if rank_data.get("code") == 20000 and rank_data.get("data"):
        plate_ranks = rank_data["data"]
        print(f"    ✅ {len(plate_ranks)} 个板块")
    else:
        plate_ranks = []
        print(f"    ⚠️  无数据")

    day_data = {
        "date": date,
        "uplimit_reason": plates,
        "uplimit_hot": hot_plates,
        "plate_rank": plate_ranks,
    }

    db.import_uplimit_day(day_data, raw_source="api")
    print(f"  💾 已写入数据库: {db.db_path}")

    return day_data


def main():
    # 加载 token
    token = load_token()
    if not token:
        print("❌ 未找到 token，请先在浏览器登录数据平台获取")
        print("   或手动将 token 保存到 config/token.json")
        return

    api = QuantAPI(token)

    # 获取交易日历
    today = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    print("获取交易日历...")
    trade_days = api.get_trade_days(end_date, days=20)  # 多取几天，确保有15个交易日
    if not trade_days:
        print("❌ 获取交易日历失败")
        return

    # 取最近15个交易日
    recent_days = trade_days[-15:]
    print(f"最近15个交易日: {recent_days[0]} ~ {recent_days[-1]}")

    db = MarketDB(DEFAULT_DB_PATH)
    db.init_schema()

    # 逐日爬取涨停数据
    all_data = []
    try:
        for day in recent_days:
            date_str = day if isinstance(day, str) else day.get("date", day)
            try:
                day_data = fetch_uplimit_data(api, date_str, db)
                all_data.append(day_data)
            except Exception as e:
                print(f"  ❌ 爬取 {date_str} 失败: {e}")

        # 采集情绪K线数据
        try:
            fetch_sentiment_data(api, db, days=15)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch sentiment data: {e}")

        # 采集大盘指数数据（实时数据，仅当天）
        print(f"\n{'='*50}")
        print("采集大盘指数数据...")
        try:
            index_result = api.get_index_trends()
            if index_result.get("code") == 200 and index_result.get("data"):
                indices = index_result["data"]
                today_str = datetime.now().strftime("%Y-%m-%d")
                count = db.import_index_daily(today_str, indices, raw_source="api")
                print(f"  ✅ 已写入 {count} 条指数数据 ({today_str})")
                for idx in indices:
                    print(f"    {idx['name']}: {idx['last_px']} ({idx['px_change_rate']}%)")
            else:
                print(f"  ⚠️  无指数数据或接口返回异常")
        except Exception as e:
            print(f"  ❌ 采集指数数据失败: {e}")
    finally:
        db.close()

    print(f"\n{'='*50}")
    print(f"✅ 完成！共爬取 {len(all_data)} 个交易日")
    print(f"📁 数据库: {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    main()
