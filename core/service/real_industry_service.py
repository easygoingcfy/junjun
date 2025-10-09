"""
真实行业数据服务
使用tushare和同花顺API获取真实的行业分类数据
"""

import tushare as ts
import requests
import time
from typing import List, Dict, Optional
from infrastructure.db.engine import get_session

class RealIndustryService:
    """真实行业数据服务"""
    
    def __init__(self, tushare_token: str = None):
        """
        初始化服务
        :param tushare_token: tushare token，如果为None则从配置文件读取
        """
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
    
    def get_stock_basic_info(self) -> List[Dict]:
        """
        获取股票基本信息，包括行业分类
        :return: 股票基本信息列表
        """
        try:
            # 获取股票基本信息
            df = self.pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            
            # 转换为字典列表
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'ts_code': row['ts_code'],
                    'symbol': row['symbol'],
                    'name': row['name'],
                    'area': row['area'],
                    'industry': row['industry'],
                    'market': row['market'],
                    'list_date': row['list_date']
                })
            
            print(f"成功获取 {len(stocks)} 只股票的基本信息")
            return stocks
            
        except Exception as e:
            print(f"获取股票基本信息失败: {e}")
            return []
    
    def get_industry_classification(self) -> List[Dict]:
        """
        获取行业分类信息
        :return: 行业分类列表
        """
        try:
            # 获取申万行业分类
            df = self.pro.index_classify(
                level='L1',
                src='SW2021'
            )
            
            industries = []
            for _, row in df.iterrows():
                industries.append({
                    'index_code': row['index_code'],
                    'industry_name': row['industry_name'],
                    'level': row['level'],
                    'src': row['src']
                })
            
            print(f"成功获取 {len(industries)} 个申万行业分类")
            return industries
            
        except Exception as e:
            print(f"获取行业分类失败: {e}")
            return []
    
    def get_industry_stocks(self, industry_code: str) -> List[str]:
        """
        获取指定行业的股票列表
        :param industry_code: 行业代码
        :return: 股票代码列表
        """
        try:
            # 获取行业成分股
            df = self.pro.index_member(
                index_code=industry_code
            )
            
            stocks = df['con_code'].tolist()
            print(f"行业 {industry_code} 包含 {len(stocks)} 只股票")
            return stocks
            
        except Exception as e:
            print(f"获取行业股票失败: {e}")
            return []
    
    def update_stock_industries_from_tushare(self) -> int:
        """
        使用tushare数据更新股票行业信息
        :return: 更新的股票数量
        """
        print("开始从tushare获取真实行业数据...")
        
        # 获取股票基本信息
        stocks = self.get_stock_basic_info()
        if not stocks:
            print("未获取到股票数据")
            return 0
        
        updated_count = 0
        with get_session() as conn:
            for stock in stocks:
                try:
                    # 更新股票行业信息
                    conn.execute(
                        "UPDATE stock_info SET industry = ? WHERE ts_code = ?",
                        (stock['industry'], stock['ts_code'])
                    )
                    updated_count += 1
                    
                    # 每1000只股票提交一次
                    if updated_count % 1000 == 0:
                        conn.commit()
                        print(f"已更新 {updated_count} 只股票...")
                        time.sleep(0.1)  # 避免请求过于频繁
                
                except Exception as e:
                    print(f"更新股票 {stock['ts_code']} 失败: {e}")
                    continue
            
            conn.commit()
        
        print(f"行业数据更新完成，共更新 {updated_count} 只股票")
        return updated_count
    
    def get_ths_industry_data(self) -> List[Dict]:
        """
        获取同花顺行业数据（备用方案）
        :return: 同花顺行业数据列表
        """
        try:
            # 同花顺行业数据API（需要根据实际情况调整）
            url = "http://q.10jqka.com.cn/stock/thshy/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # 这里需要解析同花顺的HTML页面
                # 由于同花顺的页面结构可能变化，这里提供框架
                print("同花顺数据获取成功（需要解析HTML）")
                return []
            else:
                print(f"同花顺数据获取失败: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"获取同花顺数据失败: {e}")
            return []
    
    def validate_industry_data(self) -> Dict:
        """
        验证行业数据的有效性
        :return: 验证结果
        """
        print("开始验证行业数据...")
        
        with get_session() as conn:
            # 检查行业分布
            industries = conn.execute('''
                SELECT industry, COUNT(*) as count 
                FROM stock_info 
                WHERE industry IS NOT NULL AND industry != '' 
                GROUP BY industry 
                ORDER BY count DESC
            ''').fetchall()
            
            # 检查总股票数
            total_stocks = conn.execute('SELECT COUNT(*) FROM stock_info').fetchone()[0]
            stocks_with_industry = conn.execute('SELECT COUNT(*) FROM stock_info WHERE industry IS NOT NULL AND industry != ""').fetchone()[0]
            
            # 检查K线数据匹配
            kline_matches = conn.execute('''
                SELECT COUNT(*) 
                FROM stock_info si 
                INNER JOIN daily_kline dk ON dk.ts_code LIKE si.ts_code || '.%'
                WHERE si.industry IS NOT NULL AND si.industry != ''
            ''').fetchone()[0]
            
            validation_result = {
                'total_stocks': total_stocks,
                'stocks_with_industry': stocks_with_industry,
                'industry_coverage': stocks_with_industry / total_stocks if total_stocks > 0 else 0,
                'kline_matches': kline_matches,
                'kline_match_rate': kline_matches / stocks_with_industry if stocks_with_industry > 0 else 0,
                'industry_count': len(industries),
                'top_industries': industries[:10]
            }
            
            print("验证结果:")
            print(f"总股票数: {validation_result['total_stocks']}")
            print(f"有行业信息的股票: {validation_result['stocks_with_industry']}")
            print(f"行业覆盖率: {validation_result['industry_coverage']:.2%}")
            print(f"K线数据匹配数: {validation_result['kline_matches']}")
            print(f"K线匹配率: {validation_result['kline_match_rate']:.2%}")
            print(f"行业总数: {validation_result['industry_count']}")
            print("前10个行业:")
            for industry, count in validation_result['top_industries']:
                print(f"  {industry}: {count}只股票")
            
            return validation_result
    
    def get_real_industry_stats(self, trade_date: str) -> List[Dict]:
        """
        获取真实的行业统计数据
        :param trade_date: 交易日期
        :return: 行业统计数据
        """
        with get_session() as conn:
            # 使用真实数据计算行业统计
            query = """
            SELECT 
                si.industry,
                COUNT(*) as stock_count,
                SUM(dk.vol) as total_volume,
                AVG(dk.vol) as avg_volume,
                SUM(dk.amount) as total_amount,
                AVG(dk.pct_chg) as avg_pct_chg,
                MAX(dk.pct_chg) as max_pct_chg,
                MIN(dk.pct_chg) as min_pct_chg
            FROM stock_info si
            LEFT JOIN daily_kline dk ON (
                dk.ts_code LIKE si.ts_code || '.%' AND dk.trade_date = ?
            )
            WHERE si.industry IS NOT NULL AND si.industry != ''
            GROUP BY si.industry
            ORDER BY total_volume DESC
            """
            
            rows = conn.execute(query, (trade_date,)).fetchall()
            
            return [
                {
                    "industry": row[0],
                    "stock_count": row[1],
                    "total_volume": float(row[2]) if row[2] else 0,
                    "avg_volume": float(row[3]) if row[3] else 0,
                    "total_amount": float(row[4]) if row[4] else 0,
                    "avg_pct_chg": float(row[5]) if row[5] else 0,
                    "max_pct_chg": float(row[6]) if row[6] else 0,
                    "min_pct_chg": float(row[7]) if row[7] else 0
                }
                for row in rows
            ]
