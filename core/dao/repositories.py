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


class IndustryRepository:
    """行业统计仓储"""
    def get_all_industries(self) -> List[dict]:
        """获取所有行业列表"""
        with get_session() as conn:
            rows = conn.execute("SELECT DISTINCT industry FROM stock_info WHERE industry IS NOT NULL AND industry != ''").fetchall()
            return [{"name": row[0], "id": row[0]} for row in rows]
    
    def get_industry_stats(self, days: int = 7) -> List[dict]:
        """获取行业统计数据，按最近N天总成交量排序"""
        with get_session() as conn:
            # 获取最近N天的行业统计数据
            # 先获取最新的几个交易日
            latest_dates_query = """
            SELECT DISTINCT trade_date 
            FROM industry_stats 
            ORDER BY trade_date DESC 
            LIMIT ?
            """
            latest_dates = [row[0] for row in conn.execute(latest_dates_query, (days,)).fetchall()]
            
            if not latest_dates:
                return []
            
            # 使用IN查询而不是日期减法
            placeholders = ','.join(['?' for _ in latest_dates])
            query = f"""
            SELECT 
                industry,
                SUM(total_volume) as total_volume,
                AVG(avg_pct_chg) as avg_pct_chg,
                COUNT(DISTINCT trade_date) as days_count,
                MAX(stock_count) as stock_count
            FROM industry_stats 
            WHERE trade_date IN ({placeholders})
            GROUP BY industry
            ORDER BY total_volume DESC
            """
            rows = conn.execute(query, latest_dates).fetchall()
            return [
                {
                    "id": row[0],
                    "name": row[0],
                    "total_volume": float(row[1]) if row[1] else 0,
                    "avg_pct_chg": float(row[2]) if row[2] else 0,
                    "days_count": row[3],
                    "stock_count": row[4]
                }
                for row in rows
            ]
    
    def get_stocks_by_industry(self, industry: str, sort_by: str = "volume", limit: int = 100) -> List[dict]:
        """获取指定行业的股票列表，支持多种排序方式"""
        with get_session() as conn:
            # 构建排序字段
            order_field = {
                "volume": "sds.volume DESC",
                "amount": "sds.amount DESC", 
                "pct_chg": "sds.pct_chg DESC",
                "turnover_rate": "sds.turnover_rate DESC"
            }.get(sort_by, "sds.volume DESC")
            
            query = f"""
            SELECT 
                si.ts_code,
                si.name,
                si.industry,
                dk.close,
                sds.volume,
                sds.amount,
                sds.pct_chg,
                sds.turnover_rate,
                sds.amplitude
            FROM stock_info si
            LEFT JOIN daily_kline dk ON si.ts_code = dk.ts_code 
                AND dk.trade_date = (SELECT MAX(trade_date) FROM daily_kline WHERE ts_code = si.ts_code)
            LEFT JOIN stock_daily_stats sds ON si.ts_code = sds.ts_code 
                AND sds.trade_date = (SELECT MAX(trade_date) FROM stock_daily_stats WHERE ts_code = si.ts_code)
            WHERE si.industry = ?
            ORDER BY {order_field}
            LIMIT ?
            """
            rows = conn.execute(query, (industry, limit)).fetchall()
            return [
                {
                    "ts_code": row[0].split('.')[0] if row[0] else row[0],
                    "name": row[1],
                    "industry": row[2],
                    "close": float(row[3]) if row[3] else None,
                    "volume": float(row[4]) if row[4] else 0,
                    "amount": float(row[5]) if row[5] else 0,
                    "pct_chg": float(row[6]) if row[6] else 0,
                    "turnover_rate": float(row[7]) if row[7] else 0,
                    "amplitude": float(row[8]) if row[8] else 0
                }
                for row in rows
            ]
