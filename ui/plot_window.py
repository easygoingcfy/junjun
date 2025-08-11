from PyQt5.QtWidgets import QDialog, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.dates as mdates

class PlotWindow(QDialog):
    def __init__(self, ts_code, kline, viz_cfg=None):
        super().__init__()
        self.setWindowTitle(f"{ts_code} K线图")
        layout = QVBoxLayout()
        fig = Figure(figsize=(10, 6))
        canvas = FigureCanvas(fig)
        ax_price = fig.add_subplot(2, 1, 1)
        ax_vol = fig.add_subplot(2, 1, 2, sharex=ax_price)
        # 处理数据
        import pandas as pd
        df = pd.DataFrame(kline, columns=["trade_date", "open", "high", "low", "close", "vol"])
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date').reset_index(drop=True)
        # 计算涨跌幅、均线
        df['pct_chg'] = df['close'].pct_change() * 100
        viz_cfg = viz_cfg or {}
        ma_days = viz_cfg.get('ma_days', [5, 10, 20])
        for n in ma_days:
            df[f'MA{n}'] = df['close'].rolling(n, min_periods=1).mean()
        # K线
        from matplotlib.patches import Rectangle
        width = 0.6
        x = list(range(len(df)))
        for idx, row in df.iterrows():
            o, h, low_, c = float(row['open']), float(row['high']), float(row['low']), float(row['close'])
            color = 'red' if c >= o else 'green'
            rect = Rectangle((idx - width/2, min(o, c)), width, abs(c - o), color=color, alpha=0.7)
            ax_price.add_patch(rect)
            ax_price.plot([idx, idx], [h, max(o, c)], color=color, linewidth=1)
            ax_price.plot([idx, idx], [min(o, c), low_], color=color, linewidth=1)
            # 标注涨跌幅
            pct_chg = row['pct_chg']
            if hasattr(pd, 'isna'):
                is_na = pd.isna(pct_chg)
            else:
                is_na = pd.isnull(pct_chg)
            if not is_na:
                ax_price.annotate(f"{pct_chg:.2f}%", (idx, h), textcoords="offset points", xytext=(0, 6), ha='center', fontsize=8, color=color)
        # 画均线
        for n in ma_days:
            ax_price.plot(x, df[f'MA{n}'], label=f'MA{n}', linewidth=1)
        ax_price.legend(loc='upper left', fontsize=8)
        ax_price.set_title(f"{ts_code} 区间K线图")
        ax_price.set_ylabel("价格")
        # 成交量
        ax_vol.bar(x, df['vol'], color=['red' if c>=o else 'green' for o,c in zip(df['open'], df['close'])], width=0.6, alpha=0.6)
        ax_vol.set_ylabel("成交量")
        # 形态标注（最近N根）
        patterns = viz_cfg.get('patterns', [])
        pattern_window = viz_cfg.get('pattern_window', 5)
        if patterns:
            from strategy.patterns import detect_patterns
            found = detect_patterns(df[['open','high','low','close']], patterns, pattern_window)
            for p, idxs in found.items():
                for i in idxs:
                    ax_price.annotate(p, (i, df['high'].iat[i]), textcoords="offset points", xytext=(0, 12), ha='center', fontsize=8, color='blue', rotation=45)
        # x轴
        ax_price.set_xlim(-1, len(x))
        ax_vol.set_xlim(-1, len(x))
        xticks = x[::max(1, len(x)//10)]
        ax_vol.set_xticks(xticks)
        ax_vol.set_xticklabels([df['trade_date'].dt.strftime('%Y-%m-%d').iloc[i] for i in xticks], rotation=45)
        layout.addWidget(canvas)
        self.setLayout(layout)