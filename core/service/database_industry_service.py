"""
基于数据库的行业数据服务
优先从数据库查询，避免实时联网查询
"""

import tushare as ts
import time
from typing import List, Dict, Optional, Tuple
from infrastructure.db.engine import get_session
from datetime import datetime, timedelta

class DatabaseIndustryService:
    """基于数据库的行业数据服务"""
    
    def __init__(self, tushare_token: str = None):
        """初始化服务"""
        if tushare_token:
            ts.set_token(tushare_token)
        else:
            # 从配置文件读取token
            import toml
            try:
                config = toml.load("config.local.toml")
                token = config.get("tushare", {}).get("token")
                if token:
                    ts.set_token(token)
                else:
                    raise ValueError("未找到tushare token")
            except Exception as e:
                raise ValueError(f"读取tushare配置失败: {e}")
        
        self.pro = ts.pro_api()
    
    def sync_industry_indexes(self) -> int:
        """同步行业指数信息到数据库"""
        print("开始同步行业指数信息...")
        
        try:
            # 获取申万行业分类
            df = self.pro.index_classify(level='L1', src='SW2021')
            
            with get_session() as conn:
                count = 0
                for _, row in df.iterrows():
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO industry_index 
                            (index_code, index_name, industry_name, level, src, updated_at)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (
                            row['index_code'],
                            row['index_name'], 
                            row['industry_name'],
                            row['level'],
                            row['src']
                        ))
                        count += 1
                    except Exception as e:
                        print(f"插入行业指数 {row['index_code']} 失败: {e}")
                        continue
                
                conn.commit()
                print(f"成功同步 {count} 个行业指数")
                return count
                
        except Exception as e:
            print(f"同步行业指数失败: {e}")
            return 0
    
    def sync_industry_members(self, index_code: str) -> int:
        """同步行业成分股"""
        try:
            # 获取行业成分股
            df = self.pro.index_member(index_code=index_code)
            
            with get_session() as conn:
                count = 0
                for _, row in df.iterrows():
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO industry_members 
                            (index_code, ts_code, con_date, is_new)
                            VALUES (?, ?, ?, ?)
                        """, (
                            index_code,
                            row['con_code'],
                            row.get('con_date', ''),
                            row.get('is_new', 0)
                        ))
                        count += 1
                    except Exception as e:
                        print(f"插入成分股 {row['con_code']} 失败: {e}")
                        continue
                
                conn.commit()
                print(f"行业 {index_code} 同步了 {count} 只成分股")
                return count
                
        except Exception as e:
            print(f"同步行业成分股失败: {e}")
            return 0
    
    def sync_industry_index_daily(self, index_code: str, start_date: str = None, end_date: str = None) -> int:
        """同步行业指数日线数据"""
        try:
            # 如果没有指定日期，获取最近30天
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            
            # 获取行业指数日线数据
            df = self.pro.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date
            )
            
            with get_session() as conn:
                count = 0
                for _, row in df.iterrows():
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO industry_index_daily 
                            (index_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            index_code,
                            row['trade_date'],
                            row.get('open'),
                            row.get('high'),
                            row.get('low'),
                            row.get('close'),
                            row.get('pre_close'),
                            row.get('change'),
                            row.get('pct_chg'),
                            row.get('vol'),
                            row.get('amount')
                        ))
                        count += 1
                    except Exception as e:
                        print(f"插入日线数据失败: {e}")
                        continue
                
                conn.commit()
                print(f"行业 {index_code} 同步了 {count} 条日线数据")
                return count
                
        except Exception as e:
            print(f"同步行业指数日线数据失败: {e}")
            return 0
    
    def get_industry_list(self) -> List[Dict]:
        """从数据库获取行业列表"""
        with get_session() as conn:
            rows = conn.execute("""
                SELECT index_code, index_name, industry_name, level, src
                FROM industry_index 
                WHERE is_active = 1
                ORDER BY industry_name
            """).fetchall()
            
            return [
                {
                    "index_code": row[0],
                    "index_name": row[1],
                    "industry_name": row[2],
                    "level": row[3],
                    "src": row[4]
                }
                for row in rows
            ]
    
    def get_industry_stats(self, trade_date: str = None) -> List[Dict]:
        """从数据库获取行业统计数据"""
        if not trade_date:
            # 获取最新交易日
            with get_session() as conn:
                latest_date = conn.execute("""
                    SELECT MAX(trade_date) FROM industry_index_daily
                """).fetchone()[0]
                trade_date = latest_date or datetime.now().strftime('%Y%m%d')
        
        with get_session() as conn:
            # 查询行业统计数据
            query = """
            SELECT 
                ii.industry_name,
                ii.index_code,
                COUNT(DISTINCT im.ts_code) as stock_count,
                SUM(iid.vol) as total_volume,
                AVG(iid.vol) as avg_volume,
                SUM(iid.amount) as total_amount,
                AVG(iid.pct_chg) as avg_pct_chg,
                MAX(iid.pct_chg) as max_pct_chg,
                MIN(iid.pct_chg) as min_pct_chg,
                iid.close as index_close
            FROM industry_index ii
            LEFT JOIN industry_members im ON ii.index_code = im.index_code
            LEFT JOIN industry_index_daily iid ON ii.index_code = iid.index_code AND iid.trade_date = ?
            WHERE ii.is_active = 1
            GROUP BY ii.index_code, ii.industry_name
            ORDER BY total_volume DESC
            """
            
            rows = conn.execute(query, (trade_date,)).fetchall()
            
            return [
                {
                    "industry_name": row[0],
                    "index_code": row[1],
                    "stock_count": row[2],
                    "total_volume": float(row[3]) if row[3] else 0,
                    "avg_volume": float(row[4]) if row[4] else 0,
                    "total_amount": float(row[5]) if row[5] else 0,
                    "avg_pct_chg": float(row[6]) if row[6] else 0,
                    "max_pct_chg": float(row[7]) if row[7] else 0,
                    "min_pct_chg": float(row[8]) if row[8] else 0,
                    "index_close": float(row[9]) if row[9] else 0
                }
                for row in rows
            ]
    
    def get_industry_kline(self, index_code: str, start_date: str = None, end_date: str = None, limit: int = 100) -> List[Dict]:
        """获取行业指数K线数据"""
        with get_session() as conn:
            query = """
            SELECT trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
            FROM industry_index_daily
            WHERE index_code = ?
            """
            params = [index_code]
            
            if start_date:
                query += " AND trade_date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND trade_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY trade_date DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [
                {
                    "trade_date": row[0],
                    "open": float(row[1]) if row[1] else 0,
                    "high": float(row[2]) if row[2] else 0,
                    "low": float(row[3]) if row[3] else 0,
                    "close": float(row[4]) if row[4] else 0,
                    "pre_close": float(row[5]) if row[5] else 0,
                    "change": float(row[6]) if row[6] else 0,
                    "pct_chg": float(row[7]) if row[7] else 0,
                    "vol": float(row[8]) if row[8] else 0,
                    "amount": float(row[9]) if row[9] else 0
                }
                for row in rows
            ]
    
    def get_industry_members(self, index_code: str) -> List[Dict]:
        """获取行业成分股列表"""
        with get_session() as conn:
            rows = conn.execute("""
                SELECT im.ts_code, si.name, si.industry, dk.close, dk.vol, dk.amount, dk.pct_chg
                FROM industry_members im
                LEFT JOIN stock_info si ON im.ts_code = si.ts_code
                LEFT JOIN daily_kline dk ON dk.ts_code LIKE si.ts_code || '.%' 
                    AND dk.trade_date = (SELECT MAX(trade_date) FROM daily_kline WHERE ts_code LIKE si.ts_code || '.%')
                WHERE im.index_code = ?
                ORDER BY dk.vol DESC
            """, (index_code,)).fetchall()
            
            return [
                {
                    "ts_code": row[0],
                    "name": row[1],
                    "industry": row[2],
                    "close": float(row[3]) if row[3] else 0,
                    "volume": float(row[4]) if row[4] else 0,
                    "amount": float(row[5]) if row[5] else 0,
                    "pct_chg": float(row[6]) if row[6] else 0
                }
                for row in rows
            ]
    
    def sync_all_industry_data(self) -> Dict:
        """同步所有行业数据"""
        print("开始同步所有行业数据...")
        
        result = {
            "industry_indexes": 0,
            "industry_members": 0,
            "industry_daily": 0,
            "errors": []
        }
        
        try:
            # 1. 同步行业指数
            result["industry_indexes"] = self.sync_industry_indexes()
            
            # 2. 获取行业列表
            industries = self.get_industry_list()
            
            # 3. 同步每个行业的成分股和日线数据
            for industry in industries:
                index_code = industry["index_code"]
                industry_name = industry["industry_name"]
                
                print(f"同步行业: {industry_name} ({index_code})")
                
                # 同步成分股
                members_count = self.sync_industry_members(index_code)
                result["industry_members"] += members_count
                
                # 同步日线数据
                daily_count = self.sync_industry_index_daily(index_code)
                result["industry_daily"] += daily_count
                
                # 避免请求过于频繁
                time.sleep(0.1)
            
            print("所有行业数据同步完成")
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"同步过程中出现错误: {e}")
        
        return result
