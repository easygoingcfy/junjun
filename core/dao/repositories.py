from typing import Iterable, Dict, List
from infrastructure.db.engine import get_session


class StockRepository:
    """股票信息仓储(最小实现)"""
    def get_all_codes(self) -> List[str]:
        with get_session() as conn:
            rows = conn.execute("SELECT ts_code FROM stock_info").fetchall()
            return [r[0].split('.')[0] if r and r[0] else r[0] for r in rows]

    def paged_list(self, q: str | None, limit: int, offset: int) -> tuple[List[dict], int]:
        sql = "SELECT ts_code, name, industry FROM stock_info"
        args = []
        if q:
            sql += " WHERE ts_code LIKE ? OR name LIKE ?"
            like = f"%{q}%"
            args = [like, like]
        sql_total = f"SELECT COUNT(1) FROM ({sql})"
        sql += " ORDER BY ts_code LIMIT ? OFFSET ?"
        args2 = args + [int(limit), int(offset)]
        with get_session() as conn:
            total = conn.execute(sql_total, args).fetchone()[0]
            rows = conn.execute(sql, args2).fetchall()
            items = [{"ts_code": r[0].split('.')[0] if r[0] else None, "name": r[1], "industry": r[2]} for r in rows]
            return items, int(total)

    def save_many(self, items: Iterable[dict]) -> None:
        with get_session() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR REPLACE INTO stock_info (ts_code, name, industry, list_date, market, exchange, area, is_st, list_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(
                    it.get('ts_code'), it.get('name', ''), it.get('industry', ''),
                    it.get('list_date', ''), it.get('market', ''), it.get('exchange', ''),
                    it.get('area', ''), int(it.get('is_st', 0) or 0), it.get('list_status', '')
                ) for it in items]
            )

    def info_map(self) -> Dict[str, Dict[str, str]]:
        """返回 {code: {name, industry}} 映射（code 无后缀）。"""
        with get_session() as conn:
            rows = conn.execute("SELECT ts_code, name, industry FROM stock_info").fetchall()
            result: Dict[str, Dict[str, str]] = {}
            for code, name, industry in rows:
                code_no = code.split('.')[0] if code else code
                result[code_no] = {"name": name or "-", "industry": industry or "-"}
            return result


class KlineRepository:
    """K线数据仓储(最小实现)"""
    def get_range(self, ts_code: str, start: str, end: str) -> List[tuple]:
        with get_session() as conn:
            rows = conn.execute(
                "SELECT trade_date, open, high, low, close, vol, pct_chg FROM daily_kline WHERE ts_code=? AND trade_date>=? AND trade_date<=? ORDER BY trade_date ASC",
                (ts_code, start, end)
            ).fetchall()
            return rows

    def latest_close_map(self) -> Dict[str, float]:
        with get_session() as conn:
            rows = conn.execute(
                """
                SELECT dk.ts_code, dk.close
                FROM daily_kline dk
                JOIN (
                    SELECT ts_code, MAX(trade_date) AS md
                    FROM daily_kline
                    GROUP BY ts_code
                ) t ON dk.ts_code = t.ts_code AND dk.trade_date = t.md
                """
            ).fetchall()
            result: Dict[str, float] = {}
            for code_full, close_val in rows:
                code_no = code_full.split('.')[0] if code_full else code_full
                if code_no and close_val is not None:
                    result[code_no] = float(close_val)
            return result


class StrategyRepository:
    pass


class SignalRepository:
    pass
