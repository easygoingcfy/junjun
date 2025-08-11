from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class BacktestWindow(QDialog):
    def __init__(self, backtest_result):
        super().__init__()
        self.setWindowTitle("回测结果")
        self.res = backtest_result
        layout = QVBoxLayout()

        # 概览
        s = self.res.summary or {}
        overview = QLabel(
            f"周期: {s.get('period')} | 窗口: {s.get('lookback_days')} | 前瞻: {s.get('forward_n')} | "
            f"信号数: {s.get('signals')} | 胜率: {s.get('win_rate')}% | 平均收益(前/后费): {s.get('avg_ret')}% / {s.get('avg_ret_after_fee')}% | "
            f"中位数: {s.get('median_ret')}% | 最大回撤: {s.get('mdd')}%"
        )
        layout.addWidget(overview)

        # 资金曲线图
        fig = Figure(figsize=(10, 4))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(1, 1, 1)
        df = self.res.signals.copy()
        if df is not None and not df.empty:
            # 按时间排序
            df = df.sort_values(['trade_date', 'ts_code']).reset_index(drop=True)
            eq = (1.0 + df['ret_pct_after_fee'].astype(float) / 100.0).cumprod()
            ax.plot(eq.index, eq.values, color='tab:blue', linewidth=1.5)
            ax.set_title('资金曲线（按信号顺序串行累积）')
            ax.set_ylabel('净值')
            ax.grid(True, alpha=0.3)
        layout.addWidget(canvas)

        # 明细表
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            'trade_date', 'ts_code', 'entry_close', 'exit_date', 'exit_close', 'ret_%', 'ret_%_after_fee', 'score', 'passed'
        ])
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.resize(1000, 700)
        self._populate_table()

    def _ret_to_color(self, ret):
        if ret is None:
            return QColor(240, 240, 240)
        r = max(-10.0, min(10.0, float(ret)))
        if r < 0:
            t = abs(r) / 10.0
            rr = int(255 + (244 - 255) * t)
            gg = int(255 + (67 - 255) * t)
            bb = int(255 + (54 - 255) * t)
            return QColor(rr, gg, bb)
        elif r > 0:
            t = r / 10.0
            rr = int(255 + (76 - 255) * t)
            gg = int(255 + (175 - 255) * t)
            bb = int(255 + (80 - 255) * t)
            return QColor(rr, gg, bb)
        else:
            return QColor(255, 255, 255)

    def _populate_table(self):
        df = self.res.signals
        if df is None or df.empty:
            self.table.setRowCount(0)
            return
        self.table.setRowCount(len(df))
        for i, row in df.reset_index(drop=True).iterrows():
            # trade_date
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get('trade_date', ''))))
            # ts_code
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get('ts_code', ''))))
            # entry_close
            item_entry = QTableWidgetItem()
            v_entry = float(row.get('entry_close', 0) or 0)
            item_entry.setData(Qt.DisplayRole, v_entry)
            self.table.setItem(i, 2, item_entry)
            # exit_date
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get('exit_date', ''))))
            # exit_close
            item_exit = QTableWidgetItem()
            v_exit = float(row.get('exit_close', 0) or 0)
            item_exit.setData(Qt.DisplayRole, v_exit)
            self.table.setItem(i, 4, item_exit)
            # ret_%
            item_ret = QTableWidgetItem()
            v_ret = row.get('ret_pct', None)
            if v_ret is not None:
                v_ret_f = float(v_ret)
                item_ret.setData(Qt.DisplayRole, v_ret_f)
                item_ret.setToolTip(f"{v_ret_f:.2f}%")
                item_ret.setBackground(self._ret_to_color(v_ret_f))
            else:
                item_ret.setText("-")
            item_ret.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 5, item_ret)
            # ret_%_after_fee
            item_ret2 = QTableWidgetItem()
            v_ret2 = row.get('ret_pct_after_fee', None)
            if v_ret2 is not None:
                v_ret2_f = float(v_ret2)
                item_ret2.setData(Qt.DisplayRole, v_ret2_f)
                item_ret2.setToolTip(f"{v_ret2_f:.2f}%")
                item_ret2.setBackground(self._ret_to_color(v_ret2_f))
            else:
                item_ret2.setText("-")
            item_ret2.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 6, item_ret2)
            # score
            item_score = QTableWidgetItem()
            v_score = float(row.get('score', 0) or 0)
            item_score.setData(Qt.DisplayRole, v_score)
            item_score.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 7, item_score)
            # passed
            self.table.setItem(i, 8, QTableWidgetItem(str(row.get('passed', ''))))
