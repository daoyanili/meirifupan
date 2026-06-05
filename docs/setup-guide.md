# 使用指南

## 环境要求

- Python 3.x
- 网络连接（访问 quant.zizizaizai.com）

## 第一步：获取 Token

1. 浏览器打开 https://quant.zizizaizai.com
2. 登录账号
3. 打开开发者工具（F12）→ Application → Local Storage
4. 复制 token 值

将 token 保存到 `config/token.json`：
```json
{
  "token": "你的token值"
}
```

## 第二步：爬取数据

```bash
cd /Users/admin/Desktop/obsidian/热爱生活/发家致富
python src/fetch_uplimit.py
```

脚本会：
1. 读取 token
2. 获取最近15个交易日
3. 逐日爬取涨停数据
4. 写入 `data/market_review.db`

输出示例：
```
==================================================
爬取 2026-06-01 的涨停数据...
==================================================
  [1/3] 涨停原因...
    ✅ 25 个板块, 68 只涨停股
  [2/3] 涨停梯队...
    ✅ 15 个热门板块
  [3/3] 板块排名...
    ✅ 30 个板块
  💾 已写入数据库: data/market_review.db
```

## 第三步：迁移历史 JSON

如果本地已有 `data/uplimit/uplimit_*.json`，可以先迁移到 SQLite：

```bash
python src/migrate_json_to_db.py
```

重复运行不会重复插入涨停事件。

## 第四步：启动旧看板

```bash
python -m http.server 8080
```

浏览器访问：http://localhost:8080

注意：当前 `index.html` 还是旧静态看板，读取的是 `data/uplimit/` 下的 JSON 文件。数据库迁移完成后，下一步需要增加本地服务接口，让看板改为读取 SQLite。

## 第五步：启动数据库数据页

如果要直接从 SQLite 读取并展示数据，启动本地数据服务：

```bash
python src/data_server.py
```

浏览器访问：

```text
http://127.0.0.1:8765
```

默认展示数据库里的最新交易日。也可以指定日期：

```text
http://127.0.0.1:8765/?date=2026-05-28
```

## 第六步：更新数据

每天收盘后（15:00后）重新运行爬取脚本即可获取当日数据。

## 常见问题

### Token 过期

重新从浏览器获取 token，更新 `config/token.json`。

### 数据为空

检查：
1. 当天是否为交易日
2. Token 是否有效
3. 网络连接是否正常

### 看板页面空白

1. 确认 HTTP 服务器已启动
2. 确认 `data/uplimit/` 目录下仍有旧 JSON 文件
3. 打开浏览器控制台（F12）查看错误信息
