# API 接口文档

## 基础信息

- **Base URL**: 见 `src/api_client.py` 配置
- **认证方式**: Bearer Token（JWT）
- **客户端**: `src/api_client.py`

## 涨停数据接口

### 1. 获取涨停原因（含板块、个股详情）

```
GET /v3/api/review/uplimit/reason
```

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date1 | string | 是 | 日期，格式 YYYY-MM-DD |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 100 |

**返回示例：**
```json
{
  "code": 20000,
  "data": [
    {
      "plate_code": "803023",
      "plate_name": "AI应用",
      "plate_score": 13426,
      "stocks": [...]
    }
  ]
}
```

### 2. 获取涨停梯队（热门板块）

```
GET /v3/open/review/uplimit/hot
```

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date1 | string | 是 | 日期 |
| limit | int | 否 | 数量，默认 20 |

### 3. 获取板块排名

```
GET /market/plates/17/rank
```

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date1 | string | 是 | 日期 |
| limit | int | 否 | 数量，默认 20 |

## 交易日历接口

### 获取交易日列表

```
GET /market/trade/days
```

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| day_end | string | 是 | 结束日期 |
| days | int | 否 | 获取天数，默认 15 |

## 其他接口（api_client.py 中定义）

| 方法 | 路径 | 说明 |
|------|------|------|
| get_plate_trend() | /market/plates/17/trend | 板块趋势 |
| get_plate_reason() | /market/plate/popular/reason | 板块热门原因 |
| get_lhb() | /market/lhb/list | 龙虎榜 |
| get_alerts() | /market/movement/alerts | 异动提醒 |
| get_index_trends() | /v3/market/index/trends | 大盘指数走势 |
| get_sentiment_kline() | /v2/api/sentiment/kline/day | 情绪K线 |
| get_market_hot() | /v3/api/sentiment/market/hot/day | 市场热点 |
| get_stock_kline() | /open/kline/d/{code} | 个股日K |
| get_stock_trend() | /trend/{code} | 个股分时 |
| get_stock_info() | /open/stock/{code}/info/12 | 个股信息 |

## 认证方式

在请求头中添加：
```
Authorization: Bearer <token>
```

Token 通过登录接口获取或从浏览器 localStorage 复制。
