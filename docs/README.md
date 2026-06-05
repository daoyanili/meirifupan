# 发家致富 - A股短线复盘系统

## 项目简介

A股投资助手，专注于短线复盘。自动爬取涨停数据，生成可视化看板，帮助快速掌握每日市场热点。

## 核心功能

- **涨停数据爬取**：自动爬取近15个交易日涨停数据
- **表结构存储**：写入本地 SQLite 数据库，支持去重、查询和后续分析
- **每日复盘看板**：展示涨停板块、涨停梯队、热门板块、涨停股明细
- **按天查看**：支持日期切换，每天独立展示

## 目录结构

```
发家致富/
├── index.html          # 前端看板页面
├── src/
│   ├── api_client.py   # API 客户端
│   ├── db.py           # SQLite 表结构和写入逻辑
│   ├── migrate_json_to_db.py # 历史 JSON 迁移脚本
│   └── fetch_uplimit.py # 数据爬取脚本
├── config/
│   └── settings.yaml   # 配置文件
├── data/
│   ├── market_review.db # SQLite 数据库
│   └── uplimit/        # 旧 JSON 数据，作为历史迁移来源保留
└── docs/               # 项目文档
```

## 快速开始

1. 迁移历史数据：`python src/migrate_json_to_db.py`
2. 爬取新数据：`python src/fetch_uplimit.py`
3. 启动看板：`python -m http.server 8080`
4. 访问页面：http://localhost:8080

当前 `index.html` 仍是旧静态看板，读取 `data/uplimit/` 下的 JSON。数据库底座已经准备好，后续需要增加本地服务接口后，看板才能直接读取 SQLite。

## 技术栈

- Python 3.x
- SQLite
- Vanilla JavaScript（前端）
- 第三方公开行情数据接口
