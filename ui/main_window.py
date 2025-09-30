from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QHBoxLayout,
    QDateEdit,
    QMessageBox,
    QSplitter,
    QScrollArea,
    QHeaderView,
    QProgressBar,
    QAction,
    QStatusBar,
)
from PyQt5.QtCore import QDate
import pandas as pd
from ui.plot_window import PlotWindow
from ui.backtest_window import BacktestWindow
from db.database import Database
from data.fetcher import DataFetcher
from data.save_data import DataSaver
from strategy.selector import StockSelector, StrategyConfig
from PyQt5.QtWidgets import QGroupBox, QCheckBox, QRadioButton, QSpinBox, QComboBox
# 新增用于详情弹窗的组件
from PyQt5.QtWidgets import QDialog, QTextEdit, QDialogButtonBox, QFileDialog
# 新增：用于颜色与对齐
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A股选股分析工具")
        self.resize(1200, 800)
        self.db = Database()
        self.fetcher = DataFetcher()
        self.saver = DataSaver(self.db)
        self.selector = StockSelector(self.db.conn)
        self.latest_trade_date: str | None = None
        self.refresh_latest_trade_date()
        self.init_ui()

    def refresh_latest_trade_date(self) -> str | None:
        try:
            row = self.db.conn.execute("SELECT MAX(trade_date) FROM daily_kline").fetchone()
            self.latest_trade_date = row[0] if row and row[0] else None
        except Exception:
            self.latest_trade_date = None
        return self.latest_trade_date

    def _latest_trade_qdate(self):
        if not self.latest_trade_date:
            return None
        return QDate.fromString(self.latest_trade_date, "yyyyMMdd")

    def _format_date(self, value: str | None) -> str:
        if not value:
            return "无"
        dt = QDate.fromString(value, "yyyyMMdd")
        return dt.toString("yyyy-MM-dd") if dt.isValid() else value

    def update_info_label(self, extra: str = ""):
        base = f"数据库最新交易日: {self._format_date(self.latest_trade_date)}"
        if extra:
            base = f"{base} | {extra}"
        if hasattr(self, "info_label"):
            self.info_label.setText(base)

    def init_ui(self):
        central = QWidget()
        root_layout = QVBoxLayout()
        central.setLayout(root_layout)
        self.setCentralWidget(central)

        # 添加菜单栏
        menubar = self.menuBar()
        data_menu = menubar.addMenu("数据")

        fetch_list_action = QAction("更新股票列表", self)
        fetch_list_action.triggered.connect(self.on_fetch_data)
        data_menu.addAction(fetch_list_action)

        fetch_kline_action = QAction("更新全部K线数据", self)
        fetch_kline_action.triggered.connect(self.on_fetch_kline_data)
        data_menu.addAction(fetch_kline_action)

        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)

        self.info_label = QLabel()
        root_layout.addWidget(self.info_label)

        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("执行选股")
        self.export_btn = QPushButton("导出选股结果")
        self.detail_btn = QPushButton("查看详情")
        self.bt_run_btn = QPushButton("运行回测")
        self.bt_export_btn = QPushButton("导出回测明细")
        for btn in [self.select_btn, self.export_btn, self.detail_btn, self.bt_run_btn, self.bt_export_btn]:
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        root_layout.addLayout(btn_layout)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter, 1)

        filter_scroll = QScrollArea()
        filter_scroll.setWidgetResizable(True)
        filter_widget = QWidget()
        filter_layout = QVBoxLayout()
        filter_layout.setContentsMargins(6, 6, 6, 6)
        filter_layout.setSpacing(12)
        filter_widget.setLayout(filter_layout)

        basic_group = QGroupBox("基础设置")
        basic_layout = QVBoxLayout()
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("屏蔽股票前缀:"))
        self.prefix_checkboxes = []
        for prefix in ["30", "68", "4", "8"]:
            cb = QCheckBox(prefix)
            cb.setChecked(False)
            self.prefix_checkboxes.append(cb)
            prefix_layout.addWidget(cb)
        prefix_layout.addStretch()
        basic_layout.addLayout(prefix_layout)

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("时间范围:"))
        self.radio_recent = QRadioButton("最近N天")
        self.radio_recent.setChecked(True)
        self.spin_recent = QSpinBox()
        self.spin_recent.setRange(1, 365)
        self.spin_recent.setValue(60)
        self.radio_custom = QRadioButton("自定义区间")
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        date_layout.addWidget(self.radio_recent)
        date_layout.addWidget(self.spin_recent)
        date_layout.addWidget(self.radio_custom)
        date_layout.addWidget(QLabel("起始:"))
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("结束:"))
        date_layout.addWidget(self.date_end)
        date_layout.addStretch()
        basic_layout.addLayout(date_layout)
        basic_group.setLayout(basic_layout)
        filter_layout.addWidget(basic_group)

        self.range_group = QGroupBox("涨幅筛选")
        self.range_group.setCheckable(True)
        self.range_group.setChecked(False)
        range_layout = QHBoxLayout()
        self.pct_input = QLineEdit()
        self.pct_input.setPlaceholderText("区间累计涨幅大于(%)，如8")
        self.single_pct_input = QLineEdit()
        self.single_pct_input.setPlaceholderText("单日涨幅大于(%)，如8")
        self.single_days_spin = QSpinBox()
        self.single_days_spin.setRange(1, 365)
        self.single_days_spin.setValue(20)
        range_layout.addWidget(QLabel("区间≥"))
        range_layout.addWidget(self.pct_input)
        range_layout.addWidget(QLabel("单日≥"))
        range_layout.addWidget(self.single_pct_input)
        range_layout.addWidget(QLabel("最近N日:"))
        range_layout.addWidget(self.single_days_spin)
        self.range_group.setLayout(range_layout)
        filter_layout.addWidget(self.range_group)

        self.volume_group = QGroupBox("成交量")
        self.volume_group.setCheckable(True)
        self.volume_group.setChecked(False)
        vol_layout = QHBoxLayout()
        self.volume_mode = QComboBox()
        self.volume_mode.addItems(["无", "放量突破", "缩量回调"])
        self.volume_ma_days = QSpinBox()
        self.volume_ma_days.setRange(1, 60)
        self.volume_ma_days.setValue(5)
        self.volume_ratio_min = QLineEdit()
        self.volume_ratio_min.setPlaceholderText("放量阈值，如1.5")
        self.volume_ratio_max = QLineEdit()
        self.volume_ratio_max.setPlaceholderText("缩量阈值，如0.7")
        self.cb_pullback_red = QCheckBox("回调需收阴")
        self.touch_ma_spin = QSpinBox()
        self.touch_ma_spin.setRange(0, 250)
        self.touch_ma_spin.setValue(0)
        vol_layout.addWidget(QLabel("模式:"))
        vol_layout.addWidget(self.volume_mode)
        vol_layout.addWidget(QLabel("量均线N:"))
        vol_layout.addWidget(self.volume_ma_days)
        vol_layout.addWidget(QLabel("放量≥:"))
        vol_layout.addWidget(self.volume_ratio_min)
        vol_layout.addWidget(QLabel("缩量≤:"))
        vol_layout.addWidget(self.volume_ratio_max)
        vol_layout.addWidget(self.cb_pullback_red)
        vol_layout.addWidget(QLabel("回踩MA:"))
        vol_layout.addWidget(self.touch_ma_spin)
        self.volume_group.setLayout(vol_layout)
        filter_layout.addWidget(self.volume_group)

        self.ma_group = QGroupBox("均线系统")
        self.ma_group.setCheckable(True)
        self.ma_group.setChecked(False)
        ma_layout = QHBoxLayout()
        self.ma_days_input = QLineEdit("5,10,20")
        self.ma_align_combo = QComboBox()
        self.ma_align_combo.addItems(["无", "多头", "空头"])
        self.price_above_ma_spin = QSpinBox()
        self.price_above_ma_spin.setRange(0, 250)
        self.price_above_ma_spin.setValue(0)
        ma_layout.addWidget(QLabel("MA天数:"))
        ma_layout.addWidget(self.ma_days_input)
        ma_layout.addWidget(QLabel("排列:"))
        ma_layout.addWidget(self.ma_align_combo)
        ma_layout.addWidget(QLabel("价>MA(N):"))
        ma_layout.addWidget(self.price_above_ma_spin)
        self.ma_group.setLayout(ma_layout)
        filter_layout.addWidget(self.ma_group)

        self.pattern_group = QGroupBox("K线形态")
        self.pattern_group.setCheckable(True)
        self.pattern_group.setChecked(False)
        pattern_layout = QHBoxLayout()
        self.cb_engulf = QCheckBox("吞没")
        self.cb_hammer = QCheckBox("锤子线")
        self.cb_shoot = QCheckBox("射击之星")
        self.cb_doji = QCheckBox("十字星")
        self.pattern_window_spin = QSpinBox()
        self.pattern_window_spin.setRange(1, 60)
        self.pattern_window_spin.setValue(5)
        pattern_layout.addWidget(self.cb_engulf)
        pattern_layout.addWidget(self.cb_hammer)
        pattern_layout.addWidget(self.cb_shoot)
        pattern_layout.addWidget(self.cb_doji)
        pattern_layout.addWidget(QLabel("最近N根:"))
        pattern_layout.addWidget(self.pattern_window_spin)
        self.pattern_group.setLayout(pattern_layout)
        filter_layout.addWidget(self.pattern_group)

        self.tech_group = QGroupBox("技术指标")
        self.tech_group.setCheckable(True)
        self.tech_group.setChecked(False)
        tech_layout = QHBoxLayout()
        self.breakout_n_spin = QSpinBox()
        self.breakout_n_spin.setRange(0, 250)
        self.breakout_n_spin.setValue(0)
        self.breakout_min_pct = QLineEdit()
        self.breakout_min_pct.setPlaceholderText("突破最小幅度%")
        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(0, 250)
        self.atr_period_spin.setValue(0)
        self.atr_max_pct = QLineEdit()
        self.atr_max_pct.setPlaceholderText("ATR/价≤%")
        self.cb_macd = QCheckBox("MACD")
        self.macd_rule = QComboBox()
        self.macd_rule.addItems(["hist>0", "dif>dea", "金叉"])
        self.cb_rsi = QCheckBox("RSI")
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(1, 250)
        self.rsi_period_spin.setValue(14)
        self.rsi_min = QLineEdit()
        self.rsi_min.setPlaceholderText("RSI≥")
        self.rsi_max = QLineEdit()
        self.rsi_max.setPlaceholderText("RSI≤")
        tech_layout.addWidget(QLabel("N日新高:"))
        tech_layout.addWidget(self.breakout_n_spin)
        tech_layout.addWidget(QLabel("最小突破%:"))
        tech_layout.addWidget(self.breakout_min_pct)
        tech_layout.addWidget(QLabel("ATR周期:"))
        tech_layout.addWidget(self.atr_period_spin)
        tech_layout.addWidget(QLabel("ATR过滤%:"))
        tech_layout.addWidget(self.atr_max_pct)
        tech_layout.addWidget(self.cb_macd)
        tech_layout.addWidget(self.macd_rule)
        tech_layout.addWidget(self.cb_rsi)
        tech_layout.addWidget(self.rsi_period_spin)
        tech_layout.addWidget(self.rsi_min)
        tech_layout.addWidget(self.rsi_max)
        self.tech_group.setLayout(tech_layout)
        filter_layout.addWidget(self.tech_group)

        weight_group = QGroupBox("评分权重（仅对启用项计分，自动归一化到100）")
        weight_layout = QHBoxLayout()
        self.weight_vol = QSpinBox()
        self.weight_vol.setRange(0, 100)
        self.weight_vol.setValue(30)
        self.weight_ma = QSpinBox()
        self.weight_ma.setRange(0, 100)
        self.weight_ma.setValue(20)
        self.weight_brk = QSpinBox()
        self.weight_brk.setRange(0, 100)
        self.weight_brk.setValue(25)
        self.weight_pat = QSpinBox()
        self.weight_pat.setRange(0, 100)
        self.weight_pat.setValue(15)
        self.weight_macd = QSpinBox()
        self.weight_macd.setRange(0, 100)
        self.weight_macd.setValue(5)
        self.weight_rsi = QSpinBox()
        self.weight_rsi.setRange(0, 100)
        self.weight_rsi.setValue(5)
        self.btn_reset_weights = QPushButton("重置默认")
        weight_layout.addWidget(QLabel("量能"))
        weight_layout.addWidget(self.weight_vol)
        weight_layout.addWidget(QLabel("均线"))
        weight_layout.addWidget(self.weight_ma)
        weight_layout.addWidget(QLabel("突破"))
        weight_layout.addWidget(self.weight_brk)
        weight_layout.addWidget(QLabel("形态"))
        weight_layout.addWidget(self.weight_pat)
        weight_layout.addWidget(QLabel("MACD"))
        weight_layout.addWidget(self.weight_macd)
        weight_layout.addWidget(QLabel("RSI"))
        weight_layout.addWidget(self.weight_rsi)
        weight_layout.addWidget(self.btn_reset_weights)
        weight_group.setLayout(weight_layout)
        filter_layout.addWidget(weight_group)

        bt_group = QGroupBox("回测配置")
        bt_layout = QHBoxLayout()
        self.bt_lookback = QSpinBox()
        self.bt_lookback.setRange(5, 300)
        self.bt_lookback.setValue(60)
        self.bt_forward = QSpinBox()
        self.bt_forward.setRange(1, 60)
        self.bt_forward.setValue(5)
        self.bt_fee_bps = QSpinBox()
        self.bt_fee_bps.setRange(0, 100)
        self.bt_fee_bps.setValue(3)
        self.bt_topk = QSpinBox()
        self.bt_topk.setRange(0, 200)
        self.bt_topk.setValue(0)
        self.bt_entry_mode = QComboBox()
        self.bt_entry_mode.addItems(["当日收盘买入", "次日开盘买入"])
        self.bt_exit_mode = QComboBox()
        self.bt_exit_mode.addItems(["n日后收盘卖出", "n日后开盘卖出"])
        self.bt_exclude_limit = QCheckBox("排除信号日涨停")
        self.bt_limit_th = QSpinBox()
        self.bt_limit_th.setRange(0, 20)
        self.bt_limit_th.setValue(10)
        bt_layout.addWidget(QLabel("回看窗口N:"))
        bt_layout.addWidget(self.bt_lookback)
        bt_layout.addWidget(QLabel("前瞻天数n:"))
        bt_layout.addWidget(self.bt_forward)
        bt_layout.addWidget(QLabel("单边手续费‰:"))
        bt_layout.addWidget(self.bt_fee_bps)
        bt_layout.addWidget(QLabel("每日TopK:"))
        bt_layout.addWidget(self.bt_topk)
        bt_layout.addWidget(self.bt_entry_mode)
        bt_layout.addWidget(self.bt_exit_mode)
        bt_layout.addWidget(self.bt_exclude_limit)
        bt_layout.addWidget(QLabel("涨停阈值%:"))
        bt_layout.addWidget(self.bt_limit_th)
        bt_group.setLayout(bt_layout)
        filter_layout.addWidget(bt_group)

        filter_layout.addStretch(1)
        filter_scroll.setWidget(filter_widget)
        splitter.addWidget(filter_scroll)

        table_panel = QWidget()
        table_layout = QVBoxLayout()
        table_panel.setLayout(table_layout)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "代码", "名称", "行业", "收盘价", "区间涨幅", "单日最大涨幅", "单日最大跌幅", "通过明细", "评分", "未来5日收益%"
        ])
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        for idx in range(self.table.columnCount()):
            if idx <= 2:
                header.setSectionResizeMode(idx, QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(idx, QHeaderView.Stretch)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 840])

        latest_q = self._latest_trade_qdate()
        if latest_q and latest_q.isValid():
            self.date_end.setDate(latest_q)
            self.date_start.setDate(latest_q.addDays(-self.spin_recent.value()))
        else:
            today = QDate.currentDate()
            self.date_end.setDate(today)
            self.date_start.setDate(today.addDays(-self.spin_recent.value()))
        self.toggle_date_mode()

        self.select_btn.clicked.connect(self.on_select_stock)
        self.export_btn.clicked.connect(self.on_export_excel)
        self.detail_btn.clicked.connect(self.on_view_detail)
        self.bt_run_btn.clicked.connect(self.on_run_backtest)
        self.bt_export_btn.clicked.connect(self.on_export_backtest)
        self.table.cellDoubleClicked.connect(self.on_plot_kline)
        self.radio_recent.toggled.connect(self.toggle_date_mode)
        self.radio_custom.toggled.connect(self.toggle_date_mode)
        self.btn_reset_weights.clicked.connect(self.on_reset_weights)

        self.update_info_label("欢迎使用A股选股分析工具")
        self.on_fetch_data()

    def on_fetch_kline_data(self):
        try:
            stock_df = self.fetcher.fetch_stock_list(from_db_conn=self.db.conn)
            if stock_df is None or stock_df.empty:
                QMessageBox.warning(self, "无数据", "请先获取股票列表。")
                return

            # 确定更新日期范围
            latest = self.refresh_latest_trade_date()
            if latest:
                latest_q = QDate.fromString(latest, "yyyyMMdd")
                start_q = latest_q.addDays(1) if latest_q.isValid() else QDate(2020, 1, 1)
            else:
                start_q = QDate(2020, 1, 1)

            if not start_q.isValid():
                start_q = QDate(2020, 1, 1)

            end_q = QDate.currentDate()
            if start_q > end_q:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(False)
                self.statusBar.showMessage("K线数据已是最新，无需更新。", 5000)
                QMessageBox.information(self, "提示", "数据库中的K线数据已是最新。")
                return

            start_date = start_q.toString("yyyyMMdd")
            end_date = end_q.toString("yyyyMMdd")

            ts_codes = stock_df['ts_code'].tolist()
            total = len(ts_codes)
            if total == 0:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(False)
                self.statusBar.showMessage("未找到任何股票代码。", 5000)
                QMessageBox.information(self, "提示", "股票列表为空，无法更新K线数据。")
                return
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.statusBar.showMessage(f"开始更新K线数据，从 {start_date} 到 {end_date}...")

            # 定义进度回调
            def progress_callback(code, stage):
                current_index = min(self.progress_bar.value() + 1, total)
                self.statusBar.showMessage(f"正在处理 {code}: {stage} ({current_index}/{total})")
                QApplication.processEvents()

            for i, ts_code in enumerate(ts_codes):
                self.statusBar.showMessage(f"正在更新 {ts_code} ({i + 1}/{total})")
                kline_df = self.fetcher.fetch_daily_kline(ts_code, start_date, end_date, progress_callback)

                if kline_df is not None and not kline_df.empty:
                    self.saver.save_daily_kline(ts_code, kline_df)
                    self.statusBar.showMessage(f"{ts_code} 更新完成 ({i + 1}/{total})")
                else:
                    self.statusBar.showMessage(f"{ts_code} 无新增数据 ({i + 1}/{total})")

                # 更新主进度
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents() # 保持UI响应

            self.progress_bar.setVisible(False)
            self.statusBar.showMessage("全部K线数据更新完成。", 5000)
            self.refresh_latest_trade_date()
            self.update_info_label(f"全部K线数据更新完成，共{total}只股票。")

        except Exception as e:
            self.progress_bar.setVisible(False)
            self.statusBar.showMessage("K线数据更新失败。", 5000)
            QMessageBox.critical(self, "更新失败", f"更新K线数据时发生错误: {e}")

    def toggle_date_mode(self):
        is_recent = self.radio_recent.isChecked()
        self.spin_recent.setEnabled(is_recent)
        self.date_start.setEnabled(not is_recent)
        self.date_end.setEnabled(not is_recent)

    def get_block_prefix(self) -> list[str]:
        return [cb.text() for cb in self.prefix_checkboxes if cb.isChecked()]

    def get_date_range(self) -> tuple[str, str, list[str]]:
        notes = []
        latest_q = self._latest_trade_qdate()

        if self.radio_recent.isChecked():
            days = self.spin_recent.value()
            if latest_q and latest_q.isValid():
                end = latest_q
            else:
                end = QDate.currentDate()
                notes.append("未检测到交易日数据，已使用今日日期")
            start = end.addDays(-days)
        else:
            start = self.date_start.date()
            end = self.date_end.date()
            if latest_q and latest_q.isValid() and end > latest_q:
                end = latest_q
                self.date_end.setDate(end)
                notes.append(f"结束日期已调整为 {end.toString('yyyy-MM-dd')}")
            if start > end:
                start = end
                self.date_start.setDate(start)
                notes.append("起始日期已自动调整不晚于结束日期")
        start_str = start.toString("yyyyMMdd")
        end_str = end.toString("yyyyMMdd")
        return start_str, end_str, notes

    def build_strategy_config(self, start: str, end: str) -> StrategyConfig:
        def parse_float(value: str | None) -> float | None:
            if value is None:
                return None
            txt = str(value).strip()
            if not txt:
                return None
            try:
                return float(txt)
            except ValueError:
                return None

        range_min_pct = None
        single_min_pct = None
        single_days = None
        if self.range_group.isChecked():
            range_min_val = parse_float(self.pct_input.text())
            if range_min_val is not None and range_min_val > 0:
                range_min_pct = range_min_val
            tmp_single = parse_float(self.single_pct_input.text())
            if tmp_single is not None and tmp_single > 0:
                single_min_pct = tmp_single
                single_days = int(self.single_days_spin.value())

        mode_map = {"无": None, "放量突破": "volume_breakout", "缩量回调": "volume_pullback"}
        vmode = None
        v_ma_days = int(self.volume_ma_days.value())
        v_min = None
        v_max = None
        pullback_red = None
        touch_ma = None
        if self.volume_group.isChecked():
            vmode = mode_map.get(self.volume_mode.currentText())
            if vmode == "volume_breakout":
                v_min = parse_float(self.volume_ratio_min.text())
            elif vmode == "volume_pullback":
                v_max = parse_float(self.volume_ratio_max.text())
                pullback_red = True if self.cb_pullback_red.isChecked() else None
                touch_ma_val = int(self.touch_ma_spin.value())
                touch_ma = touch_ma_val if touch_ma_val > 0 else None
            else:
                vmode = None

        ma_days = [int(x) for x in self.ma_days_input.text().replace('，', ',').split(',') if x.strip().isdigit()] or [5, 10, 20]
        align_map = {"无": None, "多头": "long", "空头": "short"}
        ma_align = None
        price_above = None
        if self.ma_group.isChecked():
            ma_align = align_map.get(self.ma_align_combo.currentText())
            price_val = int(self.price_above_ma_spin.value())
            price_above = price_val if price_val > 0 else None

        enable_patterns = []
        pattern_window = int(self.pattern_window_spin.value())
        if self.pattern_group.isChecked():
            if self.cb_engulf.isChecked():
                enable_patterns.append('bullish_engulfing')
            if self.cb_hammer.isChecked():
                enable_patterns.append('hammer')
            if self.cb_shoot.isChecked():
                enable_patterns.append('shooting_star')
            if self.cb_doji.isChecked():
                enable_patterns.append('doji')
        else:
            pattern_window = 5

        breakout_n = None
        breakout_min_pct = None
        atr_period = None
        atr_max_pct = None
        macd_en = None
        macd_rule = None
        rsi_en = None
        rsi_period = int(self.rsi_period_spin.value())
        rsi_min = None
        rsi_max = None
        if self.tech_group.isChecked():
            breakout_val = int(self.breakout_n_spin.value())
            breakout_n = breakout_val if breakout_val > 0 else None
            breakout_min_pct = parse_float(self.breakout_min_pct.text())
            atr_period_val = int(self.atr_period_spin.value())
            atr_period = atr_period_val if atr_period_val > 0 else None
            atr_max_pct = parse_float(self.atr_max_pct.text())
            if self.cb_macd.isChecked():
                macd_en = True
                macd_rule = self.macd_rule.currentText()
            if self.cb_rsi.isChecked():
                rsi_en = True
                rsi_min = parse_float(self.rsi_min.text())
                rsi_max = parse_float(self.rsi_max.text())
        else:
            rsi_period = int(self.rsi_period_spin.value())

        range_days = self.spin_recent.value() if self.radio_recent.isChecked() else None

        return StrategyConfig(
            range_increase_days=range_days,
            range_increase_min_pct=range_min_pct,
            exists_day_increase_within_days=single_days,
            exists_day_increase_min_pct=single_min_pct,
            volume_mode=vmode,
            volume_ma_days=v_ma_days,
            volume_ratio_min=v_min,
            volume_ratio_max=v_max,
            pullback_require_red=pullback_red,
            pullback_touch_ma=touch_ma,
            ma_days=ma_days,
            ma_alignment=ma_align,
            price_above_ma=price_above,
            enable_patterns=enable_patterns,
            pattern_window=pattern_window,
            pattern_params={},
            breakout_n=breakout_n,
            breakout_min_pct=breakout_min_pct,
            atr_period=atr_period,
            atr_max_pct_of_price=atr_max_pct,
            macd_enable=macd_en,
            macd_rule=macd_rule,
            rsi_enable=rsi_en,
            rsi_period=rsi_period,
            rsi_min=rsi_min,
            rsi_max=rsi_max,
        )

    def on_fetch_data(self):
        try:
            # 统一使用无后缀代码
            stock_df = self.fetcher.fetch_stock_list(from_db_conn=self.db.conn)
            if stock_df is None or stock_df.empty:
                QMessageBox.warning(self, "无数据", "无法获取股票列表，请检查数据库或网络。")
                return

            # 将最新列表写回数据库，保持信息同步
            self.saver.save_stock_list(stock_df)

            # 一次性批量查询每只股票的最新收盘价，避免逐行查询导致卡顿
            # 利用 (ts_code, trade_date) 索引，先取每个代码的最新交易日，再连接拿到 close
            close_rows = self.db.conn.execute(
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
            # 将带后缀代码标准化为无后缀，构建映射
            close_map = {}
            for code_full, close_val in close_rows:
                code_no = code_full.split('.')[0] if code_full and isinstance(code_full, str) else code_full
                if code_no and (close_val is not None):
                    close_map[code_no] = f"{float(close_val):.2f}"

            # 创建一个代码到行的映射，用于后续快速查找
            self.stock_list_map = {row['ts_code']: row for _, row in stock_df.iterrows()}

            # 填充表格前先关闭排序以提升性能
            was_sorting = self.table.isSortingEnabled()
            if was_sorting:
                self.table.setSortingEnabled(False)

            self.table.setRowCount(len(stock_df))
            for i, row in stock_df.iterrows():
                ts_code = str(row['ts_code'])  # 已是无后缀
                name = str(row.get('name', ''))
                industry = str(row.get('industry', ''))
                close = close_map.get(ts_code, "-")

                self.table.setItem(i, 0, QTableWidgetItem(ts_code))
                self.table.setItem(i, 1, QTableWidgetItem(name))
                self.table.setItem(i, 2, QTableWidgetItem(industry))
                self.table.setItem(i, 3, QTableWidgetItem(close))
                # 初始化其他列为空白
                for j in range(4, self.table.columnCount()):
                    self.table.setItem(i, j, QTableWidgetItem("-"))

            # 恢复排序
            if was_sorting:
                self.table.setSortingEnabled(True)

            self.update_info_label(f"已加载股票数：{len(stock_df)}")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载股票列表时发生错误: {e}")
            self.update_info_label("加载股票列表失败")

    def on_reset_weights(self):
        self.weight_vol.setValue(30)
        self.weight_ma.setValue(20)
        self.weight_brk.setValue(25)
        self.weight_pat.setValue(15)
        self.weight_macd.setValue(5)
        self.weight_rsi.setValue(5)

    def on_run_backtest(self):
        try:
            from strategy.backtest import Backtester
            # 获取股票列表（按当前前缀过滤）
            block_prefix = self.get_block_prefix()
            stock_df = self.fetcher.fetch_stock_list()
            if block_prefix:
                stock_df = stock_df[~stock_df['ts_code'].str.startswith(tuple(block_prefix))]
            ts_codes = stock_df['ts_code'].tolist()
            # 时间与策略
            start, end, notes = self.get_date_range()
            cfg = self.build_strategy_config(start, end)
            self.update_info_label("；".join(notes) if notes else "")
            # 参数
            lookback = int(self.bt_lookback.value())
            forward_n = int(self.bt_forward.value())
            fee = float(self.bt_fee_bps.value())
            topk = int(self.bt_topk.value())
            # 评分权重与回测器
            weights = {
                'vol': float(self.weight_vol.value()),
                'ma': float(self.weight_ma.value()),
                'brk': float(self.weight_brk.value()),
                'pat': float(self.weight_pat.value()),
                'macd': float(self.weight_macd.value()),
                'rsi': float(self.weight_rsi.value()),
            }
            entry_mode = 'next_open' if self.bt_entry_mode.currentIndex() == 1 else 'close'
            exit_mode = 'open' if self.bt_exit_mode.currentIndex() == 1 else 'close'
            exclude_limit = bool(self.bt_exclude_limit.isChecked())
            limit_th = float(self.bt_limit_th.value())
            bt = Backtester(self.db.conn)
            res = bt.run(ts_codes, start, end, cfg, lookback, forward_n, fee, topk, weights,
                         entry_mode=entry_mode, exit_mode=exit_mode,
                         exclude_limit_up=exclude_limit, limit_up_threshold=limit_th)
            self._last_backtest = res
            s = res.summary
            msg = (
                f"周期: {s.get('period')}, 窗口: {s.get('lookback_days')}, 前瞻: {s.get('forward_n')}\n"
                f"信号数: {s.get('signals')}, 胜率: {s.get('win_rate')}%\n"
                f"平均收益(含费前/后): {s.get('avg_ret')}% / {s.get('avg_ret_after_fee')}%\n"
                f"中位数收益: {s.get('median_ret')}%\n"
                f"最大回撤: {s.get('mdd')}%\n"
            )
            # 弹窗展示图形与明细
            win = BacktestWindow(res)
            win.exec_()
            # 同时给出简要汇总
            QMessageBox.information(self, "回测结果", msg)
        except Exception as e:
            QMessageBox.warning(self, "回测失败", f"{e}")

    def on_export_backtest(self):
        if not hasattr(self, '_last_backtest') or self._last_backtest is None or self._last_backtest.signals is None or self._last_backtest.signals.empty:
            QMessageBox.information(self, "提示", "无回测结果可导出，请先运行回测")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出回测明细", "backtest_signals.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                self._last_backtest.signals.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "导出成功", f"已导出到: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", f"导出失败: {e}")

    def on_export_excel(self):
        row_count = self.table.rowCount()
        if row_count <= 0:
            QMessageBox.information(self, "提示", "当前没有可导出的选股结果。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出选股结果",
            "stock_selection.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if not file_path:
            return

        headers = [self.table.horizontalHeaderItem(col).text() for col in range(self.table.columnCount())]
        data = []
        for row in range(row_count):
            row_values = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_values.append(item.text() if item else "")
            data.append(row_values)

        df = pd.DataFrame(data, columns=headers)

        try:
            if file_path.lower().endswith(".csv"):
                df.to_csv(file_path, index=False, encoding="utf-8-sig")
            else:
                df.to_excel(file_path, index=False)
            QMessageBox.information(self, "导出成功", f"选股结果已导出到:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出时发生错误: {e}")

    # 评分：按启用项的权重归一化到100分
    def _calc_score(self, checks: dict, cfg: StrategyConfig) -> float:
        items = []
        # (是否启用, 是否通过, 权重)
        items.append((cfg.volume_mode is not None, bool(checks.get('volume', False)), self.weight_vol.value()))
        items.append(((cfg.ma_alignment is not None) or (cfg.price_above_ma is not None), bool(checks.get('ma', False)), self.weight_ma.value()))
        items.append((cfg.breakout_n is not None, bool(checks.get('breakout', False)), self.weight_brk.value()))
        items.append((bool(cfg.enable_patterns), bool(checks.get('pattern', False)), self.weight_pat.value()))
        items.append((bool(cfg.macd_enable), bool(checks.get('macd', False)), self.weight_macd.value()))
        items.append((bool(cfg.rsi_enable), bool(checks.get('rsi', False)), self.weight_rsi.value()))
        total = sum(w for used, _pass, w in items if used and w > 0)
        if total <= 0:
            return 0.0
        earned = sum(w for used, _pass, w in items if used and _pass)
        score = earned / total * 100.0
        return round(score, 1)

    # 评分颜色：低分绿色→高分红色（线性渐变）
    def _score_to_color(self, score: float) -> QColor:
        s = max(0.0, min(100.0, float(score)))
        t = s / 100.0
        # 低分: 绿(76,175,80) → 高分: 红(244,67,54)
        r = int(76 + (244 - 76) * t)
        g = int(175 + (67 - 175) * t)
        b = int(80 + (54 - 80) * t)
        return QColor(r, g, b)

    def _style_score_item(self, item: QTableWidgetItem, score: float):
        color = self._score_to_color(score)
        item.setBackground(color)
        item.setForeground(QColor(255, 255, 255))
        item.setTextAlignment(Qt.AlignCenter)

    # 新增：收益颜色（亏损红→零白→盈利绿），默认以±10%为饱和
    def _ret_to_color(self, ret: float | None) -> QColor:
        if ret is None:
            return QColor(240, 240, 240)
        r = max(-10.0, min(10.0, float(ret)))
        if r < 0:
            t = abs(r) / 10.0
            # 白(255,255,255) -> 红(244,67,54)
            rr = int(255 + (244 - 255) * t)
            gg = int(255 + (67 - 255) * t)
            bb = int(255 + (54 - 255) * t)
            return QColor(rr, gg, bb)
        elif r > 0:
            t = r / 10.0
            # 白(255,255,255) -> 绿(76,175,80)
            rr = int(255 + (76 - 255) * t)
            gg = int(255 + (175 - 255) * t)
            bb = int(255 + (80 - 255) * t)
            return QColor(rr, gg, bb)
        else:
            return QColor(255, 255, 255)

    def _style_return_item(self, item: QTableWidgetItem, ret: float | None):
        color = self._ret_to_color(ret)
        item.setBackground(color)
        item.setTextAlignment(Qt.AlignCenter)

    def _forward_return_pct(self, ts_code: str, end_date: str, end_close: float, n: int = 5):
        try:
            rows = self.db.conn.execute(
                "SELECT trade_date, close FROM daily_kline WHERE ts_code=? AND trade_date>? ORDER BY trade_date ASC LIMIT ?",
                (ts_code, end_date, n)
            ).fetchall()
            if not rows or len(rows) < n or end_close is None or end_close == 0:
                return None
            last_close = rows[-1][1]
            return round((last_close - end_close) / end_close * 100.0, 2)
        except Exception:
            return None

    def _checks_summary_text(self, checks: dict, cfg: StrategyConfig) -> str:
        # 详细摘要并用于tooltip
        lines = []
        def add_line(label: str, ok: bool, detail: str = ""):
            mark = "✔" if ok else "✘"
            if detail:
                lines.append(f"{label}: {mark} | {detail}")
            else:
                lines.append(f"{label}: {mark}")
        # 量能
        if cfg.volume_mode is not None:
            mode = "放量突破" if cfg.volume_mode == 'volume_breakout' else "缩量回调"
            detail = []
            if cfg.volume_ratio_min is not None:
                detail.append(f"放量≥{cfg.volume_ratio_min}")
            if cfg.volume_ratio_max is not None:
                detail.append(f"缩量≤{cfg.volume_ratio_max}")
            if cfg.pullback_require_red:
                detail.append("回调需收阴")
            if cfg.pullback_touch_ma:
                detail.append(f"回踩MA{cfg.pullback_touch_ma}")
            add_line(f"量能[{mode}]", checks.get('volume', False), ", ".join(detail))
        # 均线
        if (cfg.ma_alignment is not None) or (cfg.price_above_ma is not None):
            detail = []
            if cfg.ma_alignment:
                detail.append(f"排列={cfg.ma_alignment}")
            if cfg.price_above_ma:
                detail.append(f"价>MA{cfg.price_above_ma}")
            add_line("均线", checks.get('ma', False), ", ".join(detail))
        # 涨幅
        if cfg.range_increase_min_pct is not None or (cfg.exists_day_increase_within_days and cfg.exists_day_increase_min_pct is not None):
            detail = []
            if cfg.range_increase_min_pct is not None:
                detail.append(f"区间≥{cfg.range_increase_min_pct}%")
            if cfg.exists_day_increase_within_days and cfg.exists_day_increase_min_pct is not None:
                detail.append(f"{cfg.exists_day_increase_within_days}日内单日≥{cfg.exists_day_increase_min_pct}%")
            add_line("涨幅", checks.get('range', False), ", ".join(detail))
        # 形态
        if cfg.enable_patterns:
            add_line("形态", checks.get('pattern', False), f"{','.join(cfg.enable_patterns)} | 窗口{cfg.pattern_window}")
        # 突破/ATR
        if cfg.breakout_n is not None:
            add_line("突破", checks.get('breakout', False), f"N={cfg.breakout_n}, 最小%={cfg.breakout_min_pct if cfg.breakout_min_pct is not None else 0}")
        if cfg.atr_period and cfg.atr_max_pct_of_price:
            add_line("ATR过滤", checks.get('atr', False), f"周期{cfg.atr_period}, ATR/价≤{cfg.atr_max_pct_of_price}%")
        # 动量
        if cfg.macd_enable:
            add_line("MACD", checks.get('macd', False), f"规则={cfg.macd_rule}")
        if cfg.rsi_enable:
            rng = []
            if cfg.rsi_min is not None:
                rng.append(f"≥{cfg.rsi_min}")
            if cfg.rsi_max is not None:
                rng.append(f"≤{cfg.rsi_max}")
            add_line("RSI", checks.get('rsi', False), f"周期{cfg.rsi_period} " + " ".join(rng))
        return "\n".join(lines) if lines else "-"

    def on_view_detail(self):
        # 选中行，弹出详细checks说明
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一行结果")
            return
        ts_code = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
        name = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        checks_text = self.table.item(row, 7).toolTip() if self.table.item(row, 7) and self.table.item(row, 7).toolTip() else (self.table.item(row, 7).text() if self.table.item(row, 7) else "")
        dlg = QDialog(self)
        dlg.setWindowTitle(f"详情 - {ts_code} {name}")
        layout = QVBoxLayout()
        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(checks_text or "无详情")
        layout.addWidget(text)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(dlg.accept)
        layout.addWidget(btns)
        dlg.setLayout(layout)
        dlg.resize(500, 400)
        dlg.exec_()

    def on_select_stock(self):
        # 禁用所有策略组，用于基础流程测试
        for group in [self.range_group, self.volume_group, self.ma_group, self.pattern_group, self.tech_group]:
            group.setChecked(False)
        
        QMessageBox.information(self, "测试模式", "所有策略已临时禁用，将返回全部股票以测试流程。")

        # 读取筛选条件
        block_prefix = self.get_block_prefix()
        start, end, notes = self.get_date_range()
        cfg = self.build_strategy_config(start, end)
        # 查询股票列表并过滤前缀
        stock_df = self.fetcher.fetch_stock_list()
        if block_prefix:
            stock_df = stock_df[~stock_df['ts_code'].str.startswith(tuple(block_prefix))]
        ts_codes = stock_df['ts_code'].tolist()
        # 执行筛选
        passed = self.selector.filter_stocks(ts_codes, start, end, cfg)
        # 展示结果，补充名称、行业与区间指标
        self.table.setRowCount(len(passed))
        for i, r in passed.reset_index(drop=True).iterrows():
            ts_code = r['ts_code']
            # 从内存中的映射快速查找，而不是遍历DataFrame
            base = self.stock_list_map.get(ts_code)
            if base is None:
                name, industry = "-", "-"
            else:
                name = str(base.get('name', ''))
                industry = str(base.get('industry', ''))
            
            # 读取区间K线计算展示列
            kline_rows = self.db.conn.execute(
                "SELECT trade_date, close, pct_chg FROM daily_kline WHERE ts_code=? AND trade_date>=? AND trade_date<=? ORDER BY trade_date ASC",
                (ts_code, start, end)
            ).fetchall()
            closes = [x[1] for x in kline_rows]
            pct_chg = (closes[-1] - closes[0]) / closes[0] * 100 if len(closes) >= 2 else 0
            single_day_pcts = [x[2] for x in kline_rows if x[2] is not None]
            max_up = max(single_day_pcts) if single_day_pcts else 0
            max_down = min(single_day_pcts) if single_day_pcts else 0
            close = closes[-1] if closes else None
            end_date = kline_rows[-1][0] if kline_rows else end
            checks = r.get('checks', {})
            # 生成详细摘要与简要标签
            detail_text = self._checks_summary_text(checks, cfg)
            short_tags = "; ".join([seg.split(':')[0] + ':' + ('✔' if '✔' in seg else '✘') for seg in detail_text.split('\n')]) if detail_text and detail_text != '-' else '-'
            score = self._calc_score(checks, cfg)
            fwd5 = self._forward_return_pct(ts_code, end_date, close, 5)

            self.table.setItem(i, 0, QTableWidgetItem(ts_code))
            self.table.setItem(i, 1, QTableWidgetItem(name))
            self.table.setItem(i, 2, QTableWidgetItem(industry))
            self.table.setItem(i, 3, QTableWidgetItem(f"{close:.2f}" if close is not None else "-"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{pct_chg:.2f}%"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{max_up:.2f}%"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{max_down:.2f}%"))
            item_detail = QTableWidgetItem(short_tags)
            item_detail.setToolTip(detail_text)
            self.table.setItem(i, 7, item_detail)
            # 评分：按数值排序 + 颜色填充（低绿高红）
            item_score = QTableWidgetItem()
            item_score.setData(Qt.DisplayRole, float(score))
            item_score.setToolTip(f"评分: {score:.1f}")
            self._style_score_item(item_score, score)
            self.table.setItem(i, 8, item_score)
            # 未来5日收益：亏损红→盈利绿，按数值排序
            item_ret = QTableWidgetItem()
            if fwd5 is not None:
                item_ret.setData(Qt.DisplayRole, float(fwd5))
                item_ret.setToolTip(f"未来5日收益: {fwd5:.2f}%")
            else:
                item_ret.setText("-")
                item_ret.setToolTip("未来5日收益: 数据不足")
            self._style_return_item(item_ret, fwd5)
            self.table.setItem(i, 9, item_ret)
        summary = f"筛选结果：{len(passed)} 只"
        if notes:
            summary = f"{summary} | {'；'.join(notes)}"
        self.update_info_label(summary)

    def on_plot_kline(self, row, col):
        ts_code = self.table.item(row, 0).text()
        # 获取当前筛选的日期区间
        start, end, _ = self.get_date_range()
        kline = self.db.conn.execute(
            "SELECT trade_date, open, high, low, close, vol FROM daily_kline WHERE ts_code=? AND trade_date>=? AND trade_date<=? ORDER BY trade_date ASC",
            (ts_code, start, end)).fetchall()
        if not kline:
            QMessageBox.warning(self, "无数据", "该股票区间无K线数据")
            return
        # 可视化配置（均线与形态）
        viz_cfg = {
            'ma_days': [int(x) for x in self.ma_days_input.text().replace('，',',').split(',') if x.strip().isdigit()],
            'patterns': [p for p, cb in (
                ('bullish_engulfing', self.cb_engulf),
                ('hammer', self.cb_hammer),
                ('shooting_star', self.cb_shoot),
                ('doji', self.cb_doji)
            ) if cb.isChecked()],
            'pattern_window': int(self.pattern_window_spin.value())
        }
        # 保证弹窗对象持有，防止被垃圾回收
        if not hasattr(self, '_plot_windows'):
            self._plot_windows = []
        win = PlotWindow(ts_code, kline, viz_cfg)
        self._plot_windows.append(win)
        win.show()
