"""Local web server that renders market data directly from SQLite."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from build_data_preview_html import DEFAULT_DB_PATH, build_html_preview


def render_path(path: str, db_path: str | Path) -> tuple[int, str, str]:
    parsed = urlparse(path)
    if parsed.path not in ("/", "/review"):
        return 404, "text/plain; charset=utf-8", "Not found"

    params = parse_qs(parsed.query)
    trade_date = params.get("date", [None])[0]
    try:
        return 200, "text/html; charset=utf-8", build_html_preview(db_path, trade_date)
    except Exception as exc:
        return 500, "text/plain; charset=utf-8", f"数据读取失败：{exc}"


def create_server(host: str, port: int, db_path: str | Path) -> ThreadingHTTPServer:
    db_path = Path(db_path)

    class DataRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            status, content_type, text = render_path(self.path, db_path)
            body = text.encode("utf-8")

            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    return ThreadingHTTPServer((host, port), DataRequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve market data from SQLite.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.db)
    print(f"Serving market data at http://{args.host}:{server.server_address[1]}")
    print(f"Database: {args.db}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
