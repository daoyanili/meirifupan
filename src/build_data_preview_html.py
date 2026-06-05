"""Build a static HTML data preview from the SQLite market database."""

from __future__ import annotations

import argparse
import html
import sqlite3
from pathlib import Path

from db_inventory import TABLE_LABELS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "market_review.db"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs"


def _cell(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def _query(conn: sqlite3.Connection, sql: str, params=()):
    return conn.execute(sql, params).fetchall()


def build_html_preview(db_path: str | Path, trade_date: str | None = None) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if trade_date is None:
            trade_date = conn.execute("select max(trade_date) from limit_up_events").fetchone()[0]
        if trade_date is None:
            raise ValueError("数据库里还没有涨停数据")

        total_stocks = conn.execute(
            "select count(*) from limit_up_events where trade_date = ?", (trade_date,)
        ).fetchone()[0]
        total_plates = conn.execute(
            "select count(distinct plate_code) from limit_up_plate_map where trade_date = ?",
            (trade_date,),
        ).fetchone()[0]
        first_board = conn.execute(
            """
            select count(*) from limit_up_events
            where trade_date = ? and (up_limit_desc like '%首板%' or up_limit_desc is null)
            """,
            (trade_date,),
        ).fetchone()[0]
        multi_board = conn.execute(
            """
            select count(*) from limit_up_events
            where trade_date = ? and up_limit_desc not like '%首板%' and up_limit_desc is not null
            """,
            (trade_date,),
        ).fetchone()[0]

        tiers = _query(
            conn,
            """
            select coalesce(up_limit_desc, '首板') as tier, count(*) as count
            from limit_up_events
            where trade_date = ?
            group by coalesce(up_limit_desc, '首板')
            order by coalesce(max(up_limit_keep_times), 1) desc, count(*) desc
            """,
            (trade_date,),
        )
        hot_plates = _query(
            conn,
            """
            select rank_no, plate_name, score
            from plate_hot_rank
            where trade_date = ?
            order by rank_no
            limit 10
            """,
            (trade_date,),
        )
        wide_plates = _query(
            conn,
            """
            select plate_name, count(distinct stock_code) as count
            from limit_up_plate_map
            where trade_date = ?
            group by plate_name
            order by count desc, plate_name
            limit 20
            """,
            (trade_date,),
        )
        top_stocks = _query(
            conn,
            """
            select stock_name, stock_code, up_limit_desc, up_limit_time, stock_price, reason
            from limit_up_events
            where trade_date = ?
            order by coalesce(up_limit_keep_times, 1) desc, up_limit_time, stock_code
            limit 60
            """,
            (trade_date,),
        )
        history = _query(
            conn,
            """
            select trade_date, count(*) as count
            from limit_up_events
            group by trade_date
            order by trade_date
            """,
        )
        inventory = [
            {
                "table_name": table,
                "label": label,
                "count": conn.execute(f"select count(*) from {table}").fetchone()[0],
            }
            for table, label in TABLE_LABELS
        ]
    finally:
        conn.close()

    max_history = max((row["count"] for row in history), default=1)

    def rows(items, columns):
        out = []
        for item in items:
            out.append("<tr>" + "".join(f"<td>{_cell(item[col])}</td>" for col in columns) + "</tr>")
        return "\n".join(out)

    history_rows = "\n".join(
        f"""
        <tr>
          <td>{_cell(row['trade_date'])}</td>
          <td>{row['count']}</td>
          <td><div class="bar"><span style="width:{row['count'] / max_history * 100:.1f}%"></span></div></td>
        </tr>
        """
        for row in history
    )

    stock_rows = "\n".join(
        f"""
        <tr>
          <td><strong>{_cell(row['stock_name'])}</strong><small>{_cell(row['stock_code'])}</small></td>
          <td>{_cell(row['up_limit_desc'] or '首板')}</td>
          <td>{_cell(row['up_limit_time'])}</td>
          <td>{_cell(row['stock_price'])}</td>
          <td class="reason">{_cell(row['reason'])}</td>
        </tr>
        """
        for row in top_stocks
    )
    inventory_rows = "\n".join(
        f"""
        <tr>
          <td>{_cell(row['label'])}<small>{_cell(row['table_name'])}</small></td>
          <td>{row['count']}</td>
          <td>{'已落库' if row['count'] else '待采集'}</td>
        </tr>
        """
        for row in inventory
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>数据预览 {html.escape(trade_date)}</title>
  <style>
    :root {{
      --bg: #f6f2ea;
      --panel: #fffdf8;
      --ink: #1f2522;
      --muted: #6a716c;
      --line: #ddd4c6;
      --red: #b9342c;
      --green: #257b5a;
      --blue: #255e91;
      --gold: #9b6a16;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
    }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 28px 24px 56px; }}
    header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 24px;
      padding-bottom: 18px;
      border-bottom: 2px solid var(--ink);
      margin-bottom: 20px;
    }}
    h1 {{ margin: 0; font-size: 32px; letter-spacing: 0; }}
    .date {{ color: var(--muted); font-size: 14px; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0 22px;
    }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .stat span {{ display:block; color: var(--muted); font-size: 12px; }}
    .stat strong {{ display:block; margin-top: 4px; font-size: 28px; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-top: 14px;
      overflow: hidden;
    }}
    h2 {{
      margin: 0;
      padding: 12px 14px;
      font-size: 16px;
      border-bottom: 1px solid var(--line);
    }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 9px 12px; border-bottom: 1px solid #eee6d9; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; background: #f3eadc; position: sticky; top: 0; }}
    td small {{ display:block; color: var(--muted); margin-top: 2px; }}
    .reason {{ max-width: 520px; color: #39413c; }}
    .bar {{ height: 8px; background: #e9dfd0; border-radius: 999px; overflow: hidden; min-width: 120px; }}
    .bar span {{ display:block; height: 100%; background: var(--red); }}
    .scroll {{ max-height: 640px; overflow: auto; }}
    .tone {{ color: var(--muted); max-width: 700px; margin: 10px 0 0; }}
    @media (max-width: 860px) {{
      main {{ padding: 18px 12px 36px; }}
      header {{ display: block; }}
      h1 {{ font-size: 24px; }}
      .stats, .grid {{ grid-template-columns: 1fr; }}
      th, td {{ padding: 8px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>市场数据预览</h1>
        <p class="tone">从 SQLite 数据库直接生成，展示去重后的涨停事件、板块分布和历史对比。</p>
      </div>
      <div class="date">交易日：{html.escape(trade_date)}</div>
    </header>

    <div class="stats">
      <div class="stat"><span>去重后涨停股</span><strong>{total_stocks}</strong></div>
      <div class="stat"><span>关联板块数</span><strong>{total_plates}</strong></div>
      <div class="stat"><span>首板</span><strong>{first_board}</strong></div>
      <div class="stat"><span>连板/多日板</span><strong>{multi_board}</strong></div>
    </div>

    <div class="grid">
      <section>
        <h2>连板结构</h2>
        <table>
          <thead><tr><th>梯队</th><th>数量</th></tr></thead>
          <tbody>{rows(tiers, ['tier', 'count'])}</tbody>
        </table>
      </section>

      <section>
        <h2>热门板块 Top 10</h2>
        <table>
          <thead><tr><th>排名</th><th>板块</th><th>热度分</th></tr></thead>
          <tbody>{rows(hot_plates, ['rank_no', 'plate_name', 'score'])}</tbody>
        </table>
      </section>
    </div>

    <section>
      <h2>覆盖涨停股最多的板块</h2>
      <table>
        <thead><tr><th>板块</th><th>关联涨停股数</th></tr></thead>
        <tbody>{rows(wide_plates, ['plate_name', 'count'])}</tbody>
      </table>
    </section>

    <section>
      <h2>涨停股明细</h2>
      <div class="scroll">
        <table>
          <thead><tr><th>股票</th><th>梯队</th><th>时间</th><th>股价</th><th>原因</th></tr></thead>
          <tbody>{stock_rows}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>历史涨停数量</h2>
      <table>
        <thead><tr><th>日期</th><th>涨停股</th><th>对比</th></tr></thead>
        <tbody>{history_rows}</tbody>
      </table>
    </section>

    <section>
      <h2>数据覆盖情况</h2>
      <table>
        <thead><tr><th>数据</th><th>行数</th><th>状态</th></tr></thead>
        <tbody>{inventory_rows}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def write_html_preview(
    db_path: str | Path = DEFAULT_DB_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    trade_date: str | None = None,
) -> Path:
    html_text = build_html_preview(db_path, trade_date)
    conn = sqlite3.connect(db_path)
    try:
        actual_date = trade_date or conn.execute("select max(trade_date) from limit_up_events").fetchone()[0]
    finally:
        conn.close()
    output_path = Path(output_dir) / f"data-preview-{actual_date}.html"
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static HTML preview from market_review.db")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--date", default=None)
    args = parser.parse_args()

    output_path = write_html_preview(args.db, args.out_dir, args.date)
    print(output_path)


if __name__ == "__main__":
    main()
