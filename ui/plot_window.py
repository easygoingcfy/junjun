from PyQt5.QtWidgets import QDialog, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.dates as mdates

class PlotWindow(QDialog):
    def __init__(self, ts_code, kline):
        super().__init__()
        self.setWindowTitle(f"{ts_code} K线图")
        layout = QVBoxLayout()
        fig = Figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        # 处理数据
        import numpy as np
        import pandas as pd
        df = pd.DataFrame(kline, columns=["trade_date", "open", "high", "low", "close", "vol"])
        # 计算涨跌幅
        df['pct_chg'] = df['close'].pct_change() * 100
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date')
        # 只用有数据的日期做x轴，避免非交易日空白
        x = list(range(len(df)))
        quotes = [(
            idx,
            float(op), float(hi), float(lo), float(cl)
        ) for idx, (op, hi, lo, cl) in enumerate(zip(df['open'], df['high'], df['low'], df['close']))]
        from matplotlib.patches import Rectangle
        width = 0.6
        for q in quotes:
            idx, open_, high, low, close = q
            color = 'red' if close >= open_ else 'green'
            rect = Rectangle((idx - width/2, min(open_, close)), width, abs(close - open_), color=color, alpha=0.7)
            ax.add_patch(rect)
            ax.plot([idx, idx], [high, max(open_, close)], color=color, linewidth=1)
            ax.plot([idx, idx], [min(open_, close), low], color=color, linewidth=1)
            # 标注涨跌幅
            pct_chg = df['pct_chg'].iloc[idx]
            if not pd.isnull(pct_chg):
                ax.annotate(f"{pct_chg:.2f}%", (idx, high), textcoords="offset points", xytext=(0, 6), ha='center', fontsize=8, color=color)
        # 设置x轴为交易日标签
        xticks = x[::max(1, len(x)//10)]
        ax.set_xticks(xticks)
        ax.set_xticklabels([df['trade_date'].dt.strftime('%Y-%m-%d').iloc[i] for i in xticks], rotation=45)
        ax.set_xlim(-1, len(x))
        ax.set_title(f"{ts_code} 区间K线图")
        ax.set_ylabel("价格")
        layout.addWidget(canvas)
        self.setLayout(layout)