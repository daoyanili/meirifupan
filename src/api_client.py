"""quant.zizizaizai.com API 客户端"""

import json
import ssl
import urllib.request
from datetime import datetime, timedelta


class QuantAPI:
    BASE_URL = "https://api.zizizaizai.com"

    def __init__(self, token: str = None):
        self.token = token
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def _get(self, path: str) -> dict:
        url = f"{self.BASE_URL}/{path}"
        req = urllib.request.Request(url)
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        resp = urllib.request.urlopen(req, context=self.ctx)
        return json.loads(resp.read())

    def login(self, email: str, password: str) -> str:
        """登录获取 token"""
        url = f"{self.BASE_URL}/login"
        data = json.dumps({"email": email, "password": password}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, context=self.ctx)
        result = json.loads(resp.read())
        # 从 localStorage 获取 token 的逻辑在调用方处理
        return result

    # ========== 交易日历 ==========

    def get_trade_days(self, end_date: str, days: int = 15) -> list:
        """获取交易日列表"""
        data = self._get(f"market/trade/days?day_end={end_date}&days={days}")
        return data.get("data", [])

    # ========== 涨停数据 ==========

    def get_uplimit_reason(self, date: str, page: int = 1, page_size: int = 100) -> dict:
        """获取涨停原因（含板块、个股详情）"""
        data = self._get(f"v3/api/review/uplimit/reason?date1={date}&page={page}&page_size={page_size}")
        return data

    def get_uplimit_hot(self, date: str, limit: int = 20) -> dict:
        """获取涨停梯队（热门板块）"""
        data = self._get(f"v3/open/review/uplimit/hot?date1={date}&limit={limit}")
        return data

    # ========== 板块数据 ==========

    def get_plate_rank(self, date: str, limit: int = 20) -> dict:
        """获取板块排名"""
        data = self._get(f"market/plates/17/rank?date1={date}&limit={limit}")
        return data

    def get_plate_trend(self, plate_code: str, start_date: str, end_date: str) -> dict:
        """获取板块趋势"""
        data = self._get(f"market/plates/17/trend?plate_code={plate_code}&day_start={start_date}&day_end={end_date}")
        return data

    def get_plate_reason(self, plate_code: str) -> dict:
        """获取板块热门原因"""
        data = self._get(f"market/plate/popular/reason?plate_code={plate_code}")
        return data

    # ========== 龙虎榜 ==========

    def get_lhb(self, date: str) -> dict:
        """获取龙虎榜"""
        data = self._get(f"market/lhb/list?date1={date}")
        return data

    # ========== 异动 ==========

    def get_alerts(self, date: str, limit: int = 200) -> dict:
        """获取异动提醒"""
        data = self._get(f"market/movement/alerts?date1={date}&type=0&limit={limit}&is_real=1")
        return data

    # ========== 大盘 ==========

    def get_index_trends(self) -> dict:
        """获取大盘指数走势"""
        data = self._get("v3/market/index/trends")
        return data

    # ========== 情绪 ==========

    def get_sentiment_kline(self, date: str, period: int = 0) -> dict:
        """获取情绪K线"""
        data = self._get(f"v2/api/sentiment/kline/day/{period}?date1={date}")
        return data

    def get_market_hot(self, date: str) -> dict:
        """获取市场热点"""
        data = self._get(f"v3/api/sentiment/market/hot/day?date={date}")
        return data

    # ========== 个股 ==========

    def get_stock_kline(self, code: str) -> dict:
        """获取个股日K"""
        data = self._get(f"open/kline/d/{code}")
        return data

    def get_stock_trend(self, code: str) -> dict:
        """获取个股分时"""
        data = self._get(f"trend/{code}")
        return data

    def get_stock_info(self, code: str) -> dict:
        """获取个股信息（含概念板块）"""
        data = self._get(f"open/stock/{code}/info/12")
        return data
