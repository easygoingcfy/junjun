#!/usr/bin/env python
"""SQLite 数据健康检查脚本。

用法示例：
    python tools/db_health_check.py --db stock_data.db --recent-threshold 3 --top-gaps 10
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sqlite3
from pathlib import Path
from typing import Iterable, Sequence


STATUS_OK = "[OK]"
STATUS_WARN = "[WARN]"
STATUS_FAIL = "[FAIL]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="检查 SQLite 数据库的关键健康指标，输出可读报告。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default="stock_data.db",
        help="数据库文件路径",
    )
    parser.add_argument(
        "--recent-threshold",
        type=int,
        default=3,
        help="允许的最新交易日与今天的最大间隔天数，超过则视为警告",
    )
    parser.add_argument(
        "--top-gaps",
        type=int,
        default=10,
        help="显示交易日落后最严重的股票数量",
    )
    return parser.parse_args()


def _print_heading(title: str) -> None:
    print(f"\n=== {title} ===")


def _print_status(status: str, message: str) -> None:
    print(f"{status} {message}")


def _fetch_scalar(conn: sqlite3.Connection, query: str, params: Sequence | None = None):
    cur = conn.cursor()
    cur.execute(query, params or [])
    row = cur.fetchone()
    return row[0] if row else None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def _count_rows(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def _count_nulls(conn: sqlite3.Connection, table: str, columns: Iterable[str]) -> dict[str, int]:
    cur = conn.cursor()
    res: dict[str, int] = {}
    for col in columns:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")
        res[col] = cur.fetchone()[0]
    return res


def _run_integrity_check(conn: sqlite3.Connection) -> tuple[bool, str]:
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check")
    result = cur.fetchone()
    if not result:
        return False, "integrity_check 未返回结果"
    message = result[0]
    return message == "ok", message


def _str_to_date(value: str | None) -> _dt.date | None:
    if not value:
        return None
    try:
        return _dt.datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def run_checks(conn: sqlite3.Connection, recent_threshold: int, top_gaps: int) -> int:
    exit_code = 0
    today = _dt.date.today()

    # 1. 完整性检查
    _print_heading("完整性检查")
    ok, msg = _run_integrity_check(conn)
    if ok:
        _print_status(STATUS_OK, "PRAGMA integrity_check: ok")
    else:
        _print_status(STATUS_FAIL, f"PRAGMA integrity_check: {msg}")
        exit_code = max(exit_code, 1)

    # 2. 表与行数
    _print_heading("表与行数")
    required_tables = {
        "stock_info": ["ts_code", "name", "industry", "list_date"],
        "daily_kline": ["ts_code", "trade_date", "close", "vol"],
    }
    existing_tables = []
    for table, cols in required_tables.items():
        if not _table_exists(conn, table):
            _print_status(STATUS_FAIL, f"表 {table} 缺失")
            exit_code = max(exit_code, 1)
            continue
        existing_tables.append(table)
        count = _count_rows(conn, table)
        _print_status(STATUS_OK, f"表 {table} 存在，记录数 {count}")
        nulls = _count_nulls(conn, table, cols)
        for col, cnt in nulls.items():
            if cnt > 0:
                status = STATUS_WARN if table != "daily_kline" or col not in ("close", "vol") else STATUS_FAIL
                _print_status(status, f"  列 {col} 存在 {cnt} 条 NULL 值")
                if status == STATUS_FAIL:
                    exit_code = max(exit_code, 1)

    if "daily_kline" not in existing_tables:
        return max(exit_code, 1)

    # 3. 日期范围与时效性
    _print_heading("交易日期范围")
    min_date = _fetch_scalar(conn, "SELECT MIN(trade_date) FROM daily_kline")
    max_date = _fetch_scalar(conn, "SELECT MAX(trade_date) FROM daily_kline")
    min_date_parsed = _str_to_date(min_date)
    max_date_parsed = _str_to_date(max_date)
    _print_status(STATUS_OK, f"最早交易日: {min_date} ({min_date_parsed})")
    _print_status(STATUS_OK, f"最新交易日: {max_date} ({max_date_parsed})")
    if max_date_parsed is None:
        _print_status(STATUS_FAIL, "无法解析最新交易日，检查 trade_date 格式")
        exit_code = max(exit_code, 1)
    else:
        delta = (today - max_date_parsed).days
        status = STATUS_OK if delta <= recent_threshold else STATUS_WARN
        _print_status(status, f"距今天 {today} 已过去 {delta} 天")
        if status == STATUS_WARN:
            exit_code = max(exit_code, 1)

    # 4. 重复记录
    _print_heading("重复记录")
    duplicate_count = _fetch_scalar(
        conn,
        "SELECT COUNT(*) FROM ("
        "SELECT ts_code, trade_date, COUNT(*) AS cnt FROM daily_kline "
        "GROUP BY ts_code, trade_date HAVING cnt > 1"
        ")",
    )
    duplicate_count = duplicate_count or 0
    if duplicate_count > 0:
        _print_status(STATUS_FAIL, f"存在 {duplicate_count} 条重复 (ts_code, trade_date) 组合")
        exit_code = max(exit_code, 1)
    else:
        _print_status(STATUS_OK, "未检测到重复 (ts_code, trade_date) 记录")

    # 5. 孤立行情记录
    _print_heading("孤立行情记录")
    orphan_rows = _fetch_scalar(
        conn,
        "SELECT COUNT(*) FROM daily_kline dk "
        "LEFT JOIN stock_info si ON dk.ts_code = si.ts_code "
        "WHERE si.ts_code IS NULL",
    ) or 0
    if orphan_rows > 0:
        _print_status(STATUS_WARN, f"存在 {orphan_rows} 条行情未匹配到 stock_info")
        exit_code = max(exit_code, 1)
    else:
        _print_status(STATUS_OK, "所有 daily_kline 记录均能匹配 stock_info")

    # 6. 缺口股票（按最新交易日排序）
    _print_heading("交易日落后股票")
    cur = conn.cursor()
    cur.execute(
        "SELECT ts_code, MAX(trade_date) AS last_trade FROM daily_kline "
        "GROUP BY ts_code ORDER BY last_trade ASC LIMIT ?",
        (top_gaps,),
    )
    rows = cur.fetchall()
    lagging = []
    for ts_code, last_trade in rows:
        last_date = _str_to_date(last_trade)
        if not last_date or not max_date_parsed:
            continue
        gap = (max_date_parsed - last_date).days
        if gap > 0:
            lagging.append((ts_code, last_trade, gap))
    if lagging:
        for ts_code, last_trade, gap in lagging:
            _print_status(
                STATUS_WARN,
                f"{ts_code}: 最近交易日 {last_trade} 落后全市场 {gap} 天",
            )
        exit_code = max(exit_code, 1)
    else:
        _print_status(STATUS_OK, "未发现交易日落后于全市场的股票")

    # 7. 关键数值缺失比例
    _print_heading("关键指标缺失统计")
    key_columns = {
        "close": "收盘价",
        "vol": "成交量",
        "pct_chg": "涨跌幅",
        "amount": "成交额",
    }
    total_rows = _count_rows(conn, "daily_kline")
    if total_rows == 0:
        _print_status(STATUS_WARN, "daily_kline 表为空，无法计算缺失比例")
    else:
        for col, label in key_columns.items():
            missing = _fetch_scalar(
                conn,
                f"SELECT COUNT(*) FROM daily_kline WHERE {col} IS NULL",
            ) or 0
            pct = missing / total_rows * 100
            status = STATUS_OK if missing == 0 else STATUS_WARN
            _print_status(status, f"{label} 缺失 {missing} 条 ({pct:.2f}%)")
            if status == STATUS_WARN:
                exit_code = max(exit_code, 1)

    return exit_code


def main() -> int:
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        _print_status(STATUS_FAIL, f"数据库文件不存在: {db_path}")
        return 1
    conn = sqlite3.connect(db_path)
    try:
        print("数据库文件:", db_path.resolve())
        print("检查时间:", _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return run_checks(conn, args.recent_threshold, args.top_gaps)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
