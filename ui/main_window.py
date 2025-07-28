from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QLineEdit, QHBoxLayout, QDateEdit, QMessageBox
from PyQt5.QtCore import QDate
from ui.plot_window import PlotWindow
from db.database import Database
from data.fetcher import DataFetcher
from strategy.selector import StockSelector
import datetime

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A股选股分析工具")
        self.resize(1000, 700)
        self.db = Database()
        self.fetcher = DataFetcher()
        self.selector = StockSelector()
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout()

        # 屏蔽前缀勾选区
        from PyQt5.QtWidgets import QGroupBox, QCheckBox, QRadioButton, QSpinBox, QButtonGroup
        block_group = QGroupBox("屏蔽股票前缀")
        block_layout = QHBoxLayout()
        self.prefix_checkboxes = []
        for prefix in ["30", "68", "4", "8"]:
            cb = QCheckBox(prefix)
            cb.setChecked(True)
            self.prefix_checkboxes.append(cb)
            block_layout.addWidget(cb)
        block_group.setLayout(block_layout)
        main_layout.addWidget(block_group)

        # 日期选择区
        date_group = QGroupBox("日期区间")
        date_layout = QHBoxLayout()
        self.radio_recent = QRadioButton("最近N天")
        self.radio_recent.setChecked(True)
        self.spin_recent = QSpinBox()
        self.spin_recent.setRange(1, 365)
        self.spin_recent.setValue(20)
        self.radio_custom = QRadioButton("自定义区间")
        self.date_start = QDateEdit(QDate.currentDate().addDays(-20))
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_start.setEnabled(False)
        self.date_end.setEnabled(False)
        date_layout.addWidget(self.radio_recent)
        date_layout.addWidget(self.spin_recent)
        date_layout.addWidget(self.radio_custom)
        date_layout.addWidget(QLabel("起始:"))
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("结束:"))
        date_layout.addWidget(self.date_end)
        date_group.setLayout(date_layout)
        main_layout.addWidget(date_group)

        # 涨幅筛选
        filter_group = QGroupBox("涨幅筛选")
        filter_layout = QHBoxLayout()
        self.pct_input = QLineEdit()
        self.pct_input.setPlaceholderText("区间累计涨幅大于(%)，如8")
        filter_layout.addWidget(QLabel("区间累计涨幅大于:"))
        filter_layout.addWidget(self.pct_input)
        self.single_pct_input = QLineEdit()
        self.single_pct_input.setPlaceholderText("单日涨幅大于(%)，如8")
        filter_layout.addWidget(QLabel("单日涨幅大于:"))
        filter_layout.addWidget(self.single_pct_input)
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # 按钮区
        btn_layout = QHBoxLayout()
        self.fetch_btn = QPushButton("获取全部股票")
        self.select_btn = QPushButton("执行选股")
        self.export_btn = QPushButton("导出选股结果")
        btn_layout.addWidget(self.fetch_btn)
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.export_btn)
        main_layout.addLayout(btn_layout)

        # 信息与表格
        self.info_label = QLabel("欢迎使用A股选股分析工具")
        main_layout.addWidget(self.info_label)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "行业", "收盘价", "区间涨幅", "单日最大涨幅", "单日最大跌幅"])
        main_layout.addWidget(self.table)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # 交互逻辑
        self.fetch_btn.clicked.connect(self.on_fetch_data)
        self.select_btn.clicked.connect(self.on_select_stock)
        self.table.cellDoubleClicked.connect(self.on_plot_kline)
        self.radio_recent.toggled.connect(self.toggle_date_mode)
        self.radio_custom.toggled.connect(self.toggle_date_mode)
        self.export_btn.clicked.connect(self.on_export_excel)
    def on_export_excel(self):
        import pandas as pd
        from PyQt5.QtWidgets import QFileDialog
        row_count = self.table.rowCount()
        col_count = self.table.columnCount()
        if row_count == 0:
            QMessageBox.information(self, "提示", "无可导出的数据！")
            return
        data = []
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(col_count)]
        for i in range(row_count):
            row = []
            for j in range(col_count):
                item = self.table.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
        df = pd.DataFrame(data, columns=headers)
        file_path, _ = QFileDialog.getSaveFileName(self, "保存为Excel", "选股结果.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            try:
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "导出成功", f"已导出到: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", f"导出Excel失败: {e}")

    def toggle_date_mode(self):
        is_recent = self.radio_recent.isChecked()
        self.spin_recent.setEnabled(is_recent)
        self.date_start.setEnabled(not is_recent)
        self.date_end.setEnabled(not is_recent)

    def get_block_prefix(self):
        return [cb.text() for cb in self.prefix_checkboxes if cb.isChecked()]

    def get_date_range(self):
        if self.radio_recent.isChecked():
            days = self.spin_recent.value()
            end = QDate.currentDate()
            start = end.addDays(-days)
        else:
            start = self.date_start.date()
            end = self.date_end.date()
        return start.toString("yyyyMMdd"), end.toString("yyyyMMdd")

    def on_fetch_data(self):
        stock_df = self.fetcher.fetch_stock_list()
        self.table.setRowCount(len(stock_df))
        for i, row in stock_df.iterrows():
            ts_code = str(row['ts_code'])
            name = str(row.get('name', ''))
            industry = str(row.get('industry', ''))
            # 查询最新收盘价
            close_row = self.db.conn.execute(
                "SELECT close FROM daily_kline WHERE ts_code=? ORDER BY trade_date DESC LIMIT 1", (ts_code,)).fetchone()
            close = f"{close_row[0]:.2f}" if close_row and close_row[0] is not None else "-"
            self.table.setItem(i, 0, QTableWidgetItem(ts_code))
            self.table.setItem(i, 1, QTableWidgetItem(name))
            self.table.setItem(i, 2, QTableWidgetItem(industry))
            self.table.setItem(i, 3, QTableWidgetItem(close))
            self.table.setItem(i, 4, QTableWidgetItem("-"))
        self.info_label.setText(f"已加载股票数：{len(stock_df)}")

    def on_select_stock(self):
        # 读取筛选条件
        block_prefix = self.get_block_prefix()
        start, end = self.get_date_range()
        pct = float(self.pct_input.text().strip() or 0)
        single_pct = float(self.single_pct_input.text().strip() or 0)
        # 查询并筛选
        stock_df = self.fetcher.fetch_stock_list()
        if block_prefix:
            stock_df = stock_df[~stock_df['ts_code'].str.startswith(tuple(block_prefix))]
        result = []
        for _, row in stock_df.iterrows():
            ts_code = row['ts_code']
            name = row.get('name', '')
            industry = row.get('industry', '')
            kline = self.db.conn.execute(
                "SELECT close, pct_chg FROM daily_kline WHERE ts_code=? AND trade_date>=? AND trade_date<=? ORDER BY trade_date ASC", 
                (ts_code, start, end)).fetchall()
            if len(kline) < 2:
                continue
            closes = [x[0] for x in kline]
            pct_chg = (closes[-1] - closes[0]) / closes[0] * 100
            single_day_pcts = [x[1] for x in kline if x[1] is not None]
            has_single = any(p is not None and p >= single_pct for p in single_day_pcts) if single_pct > 0 else True
            max_up = max(single_day_pcts) if single_day_pcts else 0
            max_down = min(single_day_pcts) if single_day_pcts else 0
            if pct_chg >= pct and has_single:
                close = closes[-1]
                result.append((ts_code, name, industry, close, pct_chg, max_up, max_down))
        self.table.setRowCount(len(result))
        for i, (ts_code, name, industry, close, pct_chg, max_up, max_down) in enumerate(result):
            self.table.setItem(i, 0, QTableWidgetItem(ts_code))
            self.table.setItem(i, 1, QTableWidgetItem(name))
            self.table.setItem(i, 2, QTableWidgetItem(industry))
            self.table.setItem(i, 3, QTableWidgetItem(f"{close:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{pct_chg:.2f}%"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{max_up:.2f}%"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{max_down:.2f}%"))

    def on_plot_kline(self, row, col):
        ts_code = self.table.item(row, 0).text()
        # 获取当前筛选的日期区间
        start, end = self.get_date_range()
        kline = self.db.conn.execute(
            "SELECT trade_date, open, high, low, close, vol FROM daily_kline WHERE ts_code=? AND trade_date>=? AND trade_date<=? ORDER BY trade_date ASC", 
            (ts_code, start, end)).fetchall()
        if not kline:
            QMessageBox.warning(self, "无数据", "该股票区间无K线数据")
            return
        # 保证弹窗对象持有，防止被垃圾回收
        if not hasattr(self, '_plot_windows'):
            self._plot_windows = []
        win = PlotWindow(ts_code, kline)
        self._plot_windows.append(win)
        win.show()
