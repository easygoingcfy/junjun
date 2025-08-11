from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QLineEdit, QHBoxLayout, QDateEdit, QMessageBox
from PyQt5.QtCore import QDate
from ui.plot_window import PlotWindow
from ui.backtest_window import BacktestWindow
from db.database import Database
from data.fetcher import DataFetcher
from strategy.selector import StockSelector, StrategyConfig
from PyQt5.QtWidgets import QGroupBox, QCheckBox, QRadioButton, QSpinBox, QComboBox
# 新增用于详情弹窗的组件
from PyQt5.QtWidgets import QDialog, QTextEdit, QDialogButtonBox, QFileDialog
# 新增：用于颜色与对齐
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor
# 新增：UI现代化组件（工具栏、停靠栏、滚动、搜索补全等）
from PyQt5.QtWidgets import QDockWidget, QToolBar, QAction, QStatusBar, QScrollArea, QWidgetAction, QCompleter, QStyle, QHeaderView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A股选股分析工具")
        self.resize(1280, 860)
        self.db = Database()
        self.fetcher = DataFetcher()
        self.selector = StockSelector(self.db.conn)
        # 主题与缓存
        self._dark_theme = True
        self._stock_list_cache = None
        self._plot_windows = []
        self._last_backtest = None
        self.settings = QSettings("junjun", "A股选股分析工具")
        self.init_ui()

    def init_ui(self):
        # =============== 样式与状态栏 ===============
        self.apply_theme(dark=True)
        self.setStatusBar(QStatusBar(self))
        self.info_label = QLabel("欢迎使用A股选股分析工具")
        self.statusBar().addPermanentWidget(self.info_label, 1)

        # =============== 左侧：筛选器（放入可滚动 Dock） ===============
        filters_container = QWidget()
        filters_layout = QVBoxLayout()
        filters_layout.setContentsMargins(8, 8, 8, 8)
        filters_layout.setSpacing(8)

        # --- 屏蔽前缀 ---
        block_group = QGroupBox("屏蔽股票前缀")
        block_layout = QHBoxLayout()
        self.prefix_checkboxes = []
        for prefix in ["30", "68", "4", "8"]:
            cb = QCheckBox(prefix)
            cb.setChecked(True)
            self.prefix_checkboxes.append(cb)
            block_layout.addWidget(cb)
        block_group.setLayout(block_layout)
        filters_layout.addWidget(block_group)

        # --- 日期区间 ---
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
        filters_layout.addWidget(date_group)

        # --- 涨幅筛选 ---
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
        self.single_days_spin = QSpinBox()
        self.single_days_spin.setRange(1, 365)
        self.single_days_spin.setValue(20)
        filter_layout.addWidget(QLabel("在最近N天内:"))
        filter_layout.addWidget(self.single_days_spin)
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)

        # --- 成交量策略 ---
        vol_group = QGroupBox("成交量")
        vol_layout = QHBoxLayout()
        self.volume_mode = QComboBox()
        self.volume_mode.addItems(["无", "放量突破", "缩量回调"])  # None | volume_breakout | volume_pullback
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
        vol_layout.addWidget(QLabel("回踩MA(N=0关闭):"))
        vol_layout.addWidget(self.touch_ma_spin)
        vol_group.setLayout(vol_layout)
        filters_layout.addWidget(vol_group)

        # --- 均线系统 ---
        ma_group = QGroupBox("均线系统")
        ma_layout = QHBoxLayout()
        self.ma_days_input = QLineEdit("5,10,20")
        self.ma_align_combo = QComboBox()
        self.ma_align_combo.addItems(["无", "多头", "空头"])  # None | long | short
        self.price_above_ma_spin = QSpinBox()
        self.price_above_ma_spin.setRange(0, 250)
        self.price_above_ma_spin.setValue(0)
        ma_layout.addWidget(QLabel("MA天数(逗号):"))
        ma_layout.addWidget(self.ma_days_input)
        ma_layout.addWidget(QLabel("排列:"))
        ma_layout.addWidget(self.ma_align_combo)
        ma_layout.addWidget(QLabel("价格在N日MA之上(0为关闭):"))
        ma_layout.addWidget(self.price_above_ma_spin)
        ma_group.setLayout(ma_layout)
        filters_layout.addWidget(ma_group)

        # --- 热度 ---
        heat_group = QGroupBox("热度(新闻条数)")
        heat_layout = QHBoxLayout()
        self.heat_min_news = QSpinBox()
        self.heat_min_news.setRange(0, 100000)
        self.heat_min_news.setValue(0)
        self.heat_window = QSpinBox()
        self.heat_window.setRange(1, 60)
        self.heat_window.setValue(5)
        heat_layout.addWidget(QLabel("最小新闻数:"))
        heat_layout.addWidget(self.heat_min_news)
        heat_layout.addWidget(QLabel("统计窗口N:"))
        heat_layout.addWidget(self.heat_window)
        heat_group.setLayout(heat_layout)
        filters_layout.addWidget(heat_group)

        # --- 技术条件 ---
        tech_group = QGroupBox("技术条件")
        tech_layout = QHBoxLayout()
        self.breakout_n_spin = QSpinBox()
        self.breakout_n_spin.setRange(0, 250)
        self.breakout_n_spin.setValue(0)
        self.breakout_min_pct = QLineEdit()
        self.breakout_min_pct.setPlaceholderText("突破最小幅度% 可空")
        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(0, 250)
        self.atr_period_spin.setValue(0)
        self.atr_max_pct = QLineEdit()
        self.atr_max_pct.setPlaceholderText("ATR/价 ≤ % 可空")
        self.cb_macd = QCheckBox("MACD")
        self.macd_rule = QComboBox()
        self.macd_rule.addItems(["hist>0", "dif>dea", "金叉"])
        self.cb_rsi = QCheckBox("RSI")
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(1, 250)
        self.rsi_period_spin.setValue(14)
        self.rsi_min = QLineEdit()
        self.rsi_min.setPlaceholderText("RSI≥ 可空")
        self.rsi_max = QLineEdit()
        self.rsi_max.setPlaceholderText("RSI≤ 可空")
        tech_layout.addWidget(QLabel("N日新高N:"))
        tech_layout.addWidget(self.breakout_n_spin)
        tech_layout.addWidget(QLabel("最小突破%:"))
        tech_layout.addWidget(self.breakout_min_pct)
        tech_layout.addWidget(QLabel("ATR周期:"))
        tech_layout.addWidget(self.atr_period_spin)
        tech_layout.addWidget(QLabel("ATR/价≤%:"))
        tech_layout.addWidget(self.atr_max_pct)
        tech_layout.addWidget(self.cb_macd)
        tech_layout.addWidget(self.macd_rule)
        tech_layout.addWidget(self.cb_rsi)
        tech_layout.addWidget(self.rsi_period_spin)
        tech_layout.addWidget(self.rsi_min)
        tech_layout.addWidget(self.rsi_max)
        tech_group.setLayout(tech_layout)
        filters_layout.addWidget(tech_group)

        # --- 板块 ---
        board_group = QGroupBox("板块")
        board_layout = QHBoxLayout()
        self.board_in_input = QLineEdit()
        self.board_in_input.setPlaceholderText("包含板块代码/名称，逗号分隔")
        self.board_out_input = QLineEdit()
        self.board_out_input.setPlaceholderText("排除板块代码/名称，逗号分隔")
        board_layout.addWidget(QLabel("包含:"))
        board_layout.addWidget(self.board_in_input)
        board_layout.addWidget(QLabel("排除:"))
        board_layout.addWidget(self.board_out_input)
        board_group.setLayout(board_layout)
        filters_layout.addWidget(board_group)

        # --- 形态 ---
        pattern_group = QGroupBox("K线形态")
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
        pattern_layout.addWidget(QLabel("检测最近N根:"))
        pattern_layout.addWidget(self.pattern_window_spin)
        pattern_group.setLayout(pattern_layout)
        filters_layout.addWidget(pattern_group)

        # --- 评分权重 ---
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
        filters_layout.addWidget(weight_group)

        # --- 回测配置 ---
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
        self.bt_entry_mode.addItems(["当日收盘买入", "次日开盘买入"])  # close | next_open
        self.bt_exit_mode = QComboBox()
        self.bt_exit_mode.addItems(["n日后收盘卖出", "n日后开盘卖出"])  # close | open
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
        bt_layout.addWidget(QLabel("每日TopK(0不限):"))
        bt_layout.addWidget(self.bt_topk)
        bt_layout.addWidget(self.bt_entry_mode)
        bt_layout.addWidget(self.bt_exit_mode)
        bt_layout.addWidget(self.bt_exclude_limit)
        bt_layout.addWidget(QLabel("涨停阈值%:"))
        bt_layout.addWidget(self.bt_limit_th)
        bt_group.setLayout(bt_layout)
        filters_layout.addWidget(bt_group)

        filters_layout.addStretch(1)
        filters_container.setLayout(filters_layout)
        scroll = QScrollArea()
        scroll.setWidget(filters_container)
        scroll.setWidgetResizable(True)
        self.left_dock = QDockWidget("筛选条件", self)
        self.left_dock.setWidget(scroll)
        self.left_dock.setObjectName("dock_filters")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

        # =============== 中央：结果表格 ===============
        central = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(8, 8, 8, 8)

        # 顶部快速提示与搜索条（工具栏中提供更合适，这里仅放表格）
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "行业", "收盘价", "区间涨幅", "单日最大涨幅", "单日最大跌幅", "通过明细", "评分", "未来5日收益%"])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        central_layout.addWidget(self.table)
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # =============== 右侧：详情面板 ===============
        self.detail_panel = QWidget()
        dlayout = QVBoxLayout()
        dlayout.setContentsMargins(8, 8, 8, 8)
        self.detail_title = QLabel("选中行详情")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        dlayout.addWidget(self.detail_title)
        dlayout.addWidget(self.detail_text, 1)
        self.detail_panel.setLayout(dlayout)
        self.right_dock = QDockWidget("详情", self)
        self.right_dock.setObjectName("dock_detail")
        self.right_dock.setWidget(self.detail_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        # =============== 顶部工具栏 ===============
        self.init_toolbar()

        # =============== 信号连接 ===============
        self.table.cellDoubleClicked.connect(self.on_plot_kline)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.radio_recent.toggled.connect(self.toggle_date_mode)
        self.radio_custom.toggled.connect(self.toggle_date_mode)
        self.btn_reset_weights.clicked.connect(self.on_reset_weights)

        # 还原窗口布局
        try:
            geo = self.settings.value("main/geometry")
            state = self.settings.value("main/state")
            if geo:
                self.restoreGeometry(geo)
            if state:
                self.restoreState(state)
        except Exception:
            pass

        # 初始信息
        self.set_info("准备就绪")

    # 主题样式
    def apply_theme(self, dark: bool = True):
        self._dark_theme = dark
        if dark:
            qss = """
            QWidget { background-color: #121212; color: #E0E0E0; }
            QGroupBox { border: 1px solid #2A2A2A; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #BDBDBD; }
            QToolBar { background: #1E1E1E; border-bottom: 1px solid #2A2A2A; }
            QStatusBar { background: #1E1E1E; }
            QTableWidget { gridline-color: #2A2A2A; }
            QHeaderView::section { background-color: #1E1E1E; color: #BDBDBD; border: 1px solid #2A2A2A; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 4px; padding: 3px; }
            QPushButton { background: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #383838; }
            QDockWidget::title { text-align: left; padding-left: 6px; }
            QScrollBar:vertical { background: #1A1A1A; width: 10px; }
            QScrollBar::handle:vertical { background: #3A3A3A; min-height: 30px; border-radius: 4px; }
            """
        else:
            qss = """
            QWidget { background-color: #FAFAFA; color: #212121; }
            QGroupBox { border: 1px solid #DDDDDD; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #616161; }
            QToolBar { background: #F5F5F5; border-bottom: 1px solid #E0E0E0; }
            QStatusBar { background: #F5F5F5; }
            QHeaderView::section { background-color: #F5F5F5; color: #616161; border: 1px solid #E0E0E0; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 3px; }
            QPushButton { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #FAFAFA; }
            """
        self.setStyleSheet(qss)

    def init_toolbar(self):
        tb = QToolBar("主工具栏", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, tb)

        # 标准图标
        st = self.style()
        icon_refresh = st.standardIcon(QStyle.SP_BrowserReload)
        icon_run = st.standardIcon(QStyle.SP_MediaPlay)
        icon_export = st.standardIcon(QStyle.SP_DialogSaveButton)
        icon_info = st.standardIcon(QStyle.SP_MessageBoxInformation)
        icon_theme = st.standardIcon(QStyle.SP_DialogHelpButton)

        act_fetch = QAction(icon_refresh, "获取全部股票", self)
        act_fetch.triggered.connect(self.on_fetch_data)
        act_fetch.setShortcut("Ctrl+R")
        tb.addAction(act_fetch)

        act_select = QAction(icon_run, "执行选股", self)
        act_select.triggered.connect(self.on_select_stock)
        act_select.setShortcut("F5")
        tb.addAction(act_select)

        act_export = QAction(icon_export, "导出选股结果", self)
        act_export.triggered.connect(self.on_export_excel)
        act_export.setShortcut("Ctrl+E")
        tb.addAction(act_export)

        tb.addSeparator()

        act_detail = QAction(icon_info, "查看详情", self)
        act_detail.triggered.connect(self.on_view_detail)
        act_detail.setShortcut("Enter")
        tb.addAction(act_detail)

        tb.addSeparator()

        act_bt_run = QAction(icon_run, "运行回测", self)
        act_bt_run.triggered.connect(self.on_run_backtest)
        act_bt_run.setShortcut("Ctrl+B")
        tb.addAction(act_bt_run)

        act_bt_export = QAction(icon_export, "导出回测明细", self)
        act_bt_export.triggered.connect(self.on_export_backtest)
        act_bt_export.setShortcut("Ctrl+Shift+E")
        tb.addAction(act_bt_export)

        tb.addSeparator()

        # 重置评分权重
        act_reset_weights = QAction("重置权重", self)
        act_reset_weights.triggered.connect(self.on_reset_weights)
        tb.addAction(act_reset_weights)

        # 主题切换
        act_theme = QAction(icon_theme, "切换主题", self)
        def _toggle_theme():
            self.apply_theme(dark=not self._dark_theme)
        act_theme.triggered.connect(_toggle_theme)
        act_theme.setShortcut("Ctrl+T")
        tb.addAction(act_theme)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索代码/名称  回车筛选/清空恢复")
        self.search_edit.returnPressed.connect(self.apply_table_search)
        wa = QWidgetAction(self)
        wa.setDefaultWidget(self.search_edit)
        tb.addAction(wa)

    def init_ui(self):
        # 主题与状态栏和 Dock 等已在上一段定义，这里继续原实现
        self.apply_theme(dark=True)
        self.setStatusBar(QStatusBar(self))
        self.info_label = QLabel("欢迎使用A股选股分析工具")
        self.statusBar().addPermanentWidget(self.info_label, 1)

        # =============== 左侧：筛选器（放入可滚动 Dock） ===============
        filters_container = QWidget()
        filters_layout = QVBoxLayout()
        filters_layout.setContentsMargins(8, 8, 8, 8)
        filters_layout.setSpacing(8)

        # --- 屏蔽前缀 ---
        block_group = QGroupBox("屏蔽股票前缀")
        block_layout = QHBoxLayout()
        self.prefix_checkboxes = []
        for prefix in ["30", "68", "4", "8"]:
            cb = QCheckBox(prefix)
            cb.setChecked(True)
            self.prefix_checkboxes.append(cb)
            block_layout.addWidget(cb)
        block_group.setLayout(block_layout)
        filters_layout.addWidget(block_group)

        # --- 日期区间 ---
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
        filters_layout.addWidget(date_group)

        # --- 涨幅筛选 ---
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
        self.single_days_spin = QSpinBox()
        self.single_days_spin.setRange(1, 365)
        self.single_days_spin.setValue(20)
        filter_layout.addWidget(QLabel("在最近N天内:"))
        filter_layout.addWidget(self.single_days_spin)
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)

        # --- 成交量策略 ---
        vol_group = QGroupBox("成交量")
        vol_layout = QHBoxLayout()
        self.volume_mode = QComboBox()
        self.volume_mode.addItems(["无", "放量突破", "缩量回调"])  # None | volume_breakout | volume_pullback
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
        vol_layout.addWidget(QLabel("回踩MA(N=0关闭):"))
        vol_layout.addWidget(self.touch_ma_spin)
        vol_group.setLayout(vol_layout)
        filters_layout.addWidget(vol_group)

        # --- 均线系统 ---
        ma_group = QGroupBox("均线系统")
        ma_layout = QHBoxLayout()
        self.ma_days_input = QLineEdit("5,10,20")
        self.ma_align_combo = QComboBox()
        self.ma_align_combo.addItems(["无", "多头", "空头"])  # None | long | short
        self.price_above_ma_spin = QSpinBox()
        self.price_above_ma_spin.setRange(0, 250)
        self.price_above_ma_spin.setValue(0)
        ma_layout.addWidget(QLabel("MA天数(逗号):"))
        ma_layout.addWidget(self.ma_days_input)
        ma_layout.addWidget(QLabel("排列:"))
        ma_layout.addWidget(self.ma_align_combo)
        ma_layout.addWidget(QLabel("价格在N日MA之上(0为关闭):"))
        ma_layout.addWidget(self.price_above_ma_spin)
        ma_group.setLayout(ma_layout)
        filters_layout.addWidget(ma_group)

        # --- 热度 ---
        heat_group = QGroupBox("热度(新闻条数)")
        heat_layout = QHBoxLayout()
        self.heat_min_news = QSpinBox()
        self.heat_min_news.setRange(0, 100000)
        self.heat_min_news.setValue(0)
        self.heat_window = QSpinBox()
        self.heat_window.setRange(1, 60)
        self.heat_window.setValue(5)
        heat_layout.addWidget(QLabel("最小新闻数:"))
        heat_layout.addWidget(self.heat_min_news)
        heat_layout.addWidget(QLabel("统计窗口N:"))
        heat_layout.addWidget(self.heat_window)
        heat_group.setLayout(heat_layout)
        filters_layout.addWidget(heat_group)

        # --- 技术条件 ---
        tech_group = QGroupBox("技术条件")
        tech_layout = QHBoxLayout()
        self.breakout_n_spin = QSpinBox()
        self.breakout_n_spin.setRange(0, 250)
        self.breakout_n_spin.setValue(0)
        self.breakout_min_pct = QLineEdit()
        self.breakout_min_pct.setPlaceholderText("突破最小幅度% 可空")
        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(0, 250)
        self.atr_period_spin.setValue(0)
        self.atr_max_pct = QLineEdit()
        self.atr_max_pct.setPlaceholderText("ATR/价 ≤ % 可空")
        self.cb_macd = QCheckBox("MACD")
        self.macd_rule = QComboBox()
        self.macd_rule.addItems(["hist>0", "dif>dea", "金叉"])
        self.cb_rsi = QCheckBox("RSI")
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(1, 250)
        self.rsi_period_spin.setValue(14)
        self.rsi_min = QLineEdit()
        self.rsi_min.setPlaceholderText("RSI≥ 可空")
        self.rsi_max = QLineEdit()
        self.rsi_max.setPlaceholderText("RSI≤ 可空")
        tech_layout.addWidget(QLabel("N日新高N:"))
        tech_layout.addWidget(self.breakout_n_spin)
        tech_layout.addWidget(QLabel("最小突破%:"))
        tech_layout.addWidget(self.breakout_min_pct)
        tech_layout.addWidget(QLabel("ATR周期:"))
        tech_layout.addWidget(self.atr_period_spin)
        tech_layout.addWidget(QLabel("ATR/价≤%:"))
        tech_layout.addWidget(self.atr_max_pct)
        tech_layout.addWidget(self.cb_macd)
        tech_layout.addWidget(self.macd_rule)
        tech_layout.addWidget(self.cb_rsi)
        tech_layout.addWidget(self.rsi_period_spin)
        tech_layout.addWidget(self.rsi_min)
        tech_layout.addWidget(self.rsi_max)
        tech_group.setLayout(tech_layout)
        filters_layout.addWidget(tech_group)

        # --- 板块 ---
        board_group = QGroupBox("板块")
        board_layout = QHBoxLayout()
        self.board_in_input = QLineEdit()
        self.board_in_input.setPlaceholderText("包含板块代码/名称，逗号分隔")
        self.board_out_input = QLineEdit()
        self.board_out_input.setPlaceholderText("排除板块代码/名称，逗号分隔")
        board_layout.addWidget(QLabel("包含:"))
        board_layout.addWidget(self.board_in_input)
        board_layout.addWidget(QLabel("排除:"))
        board_layout.addWidget(self.board_out_input)
        board_group.setLayout(board_layout)
        filters_layout.addWidget(board_group)

        # --- 形态 ---
        pattern_group = QGroupBox("K线形态")
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
        pattern_layout.addWidget(QLabel("检测最近N根:"))
        pattern_layout.addWidget(self.pattern_window_spin)
        pattern_group.setLayout(pattern_layout)
        filters_layout.addWidget(pattern_group)

        # --- 评分权重 ---
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
        filters_layout.addWidget(weight_group)

        # --- 回测配置 ---
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
        self.bt_entry_mode.addItems(["当日收盘买入", "次日开盘买入"])  # close | next_open
        self.bt_exit_mode = QComboBox()
        self.bt_exit_mode.addItems(["n日后收盘卖出", "n日后开盘卖出"])  # close | open
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
        bt_layout.addWidget(QLabel("每日TopK(0不限):"))
        bt_layout.addWidget(self.bt_topk)
        bt_layout.addWidget(self.bt_entry_mode)
        bt_layout.addWidget(self.bt_exit_mode)
        bt_layout.addWidget(self.bt_exclude_limit)
        bt_layout.addWidget(QLabel("涨停阈值%:"))
        bt_layout.addWidget(self.bt_limit_th)
        bt_group.setLayout(bt_layout)
        filters_layout.addWidget(bt_group)

        filters_layout.addStretch(1)
        filters_container.setLayout(filters_layout)
        scroll = QScrollArea()
        scroll.setWidget(filters_container)
        scroll.setWidgetResizable(True)
        self.left_dock = QDockWidget("筛选条件", self)
        self.left_dock.setWidget(scroll)
        self.left_dock.setObjectName("dock_filters")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

        # =============== 中央：结果表格 ===============
        central = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(8, 8, 8, 8)

        # 顶部快速提示与搜索条（工具栏中提供更合适，这里仅放表格）
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "行业", "收盘价", "区间涨幅", "单日最大涨幅", "单日最大跌幅", "通过明细", "评分", "未来5日收益%"])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        central_layout.addWidget(self.table)
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # =============== 右侧：详情面板 ===============
        self.detail_panel = QWidget()
        dlayout = QVBoxLayout()
        dlayout.setContentsMargins(8, 8, 8, 8)
        self.detail_title = QLabel("选中行详情")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        dlayout.addWidget(self.detail_title)
        dlayout.addWidget(self.detail_text, 1)
        self.detail_panel.setLayout(dlayout)
        self.right_dock = QDockWidget("详情", self)
        self.right_dock.setObjectName("dock_detail")
        self.right_dock.setWidget(self.detail_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        # =============== 顶部工具栏 ===============
        self.init_toolbar()

        # =============== 信号连接 ===============
        self.table.cellDoubleClicked.connect(self.on_plot_kline)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.radio_recent.toggled.connect(self.toggle_date_mode)
        self.radio_custom.toggled.connect(self.toggle_date_mode)
        self.btn_reset_weights.clicked.connect(self.on_reset_weights)

        # 还原窗口布局
        try:
            geo = self.settings.value("main/geometry")
            state = self.settings.value("main/state")
            if geo:
                self.restoreGeometry(geo)
            if state:
                self.restoreState(state)
        except Exception:
            pass

        # 初始信息
        self.set_info("准备就绪")

    # 主题样式
    def apply_theme(self, dark: bool = True):
        self._dark_theme = dark
        if dark:
            qss = """
            QWidget { background-color: #121212; color: #E0E0E0; }
            QGroupBox { border: 1px solid #2A2A2A; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #BDBDBD; }
            QToolBar { background: #1E1E1E; border-bottom: 1px solid #2A2A2A; }
            QStatusBar { background: #1E1E1E; }
            QTableWidget { gridline-color: #2A2A2A; }
            QHeaderView::section { background-color: #1E1E1E; color: #BDBDBD; border: 1px solid #2A2A2A; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 4px; padding: 3px; }
            QPushButton { background: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #383838; }
            QDockWidget::title { text-align: left; padding-left: 6px; }
            QScrollBar:vertical { background: #1A1A1A; width: 10px; }
            QScrollBar::handle:vertical { background: #3A3A3A; min-height: 30px; border-radius: 4px; }
            """
        else:
            qss = """
            QWidget { background-color: #FAFAFA; color: #212121; }
            QGroupBox { border: 1px solid #DDDDDD; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #616161; }
            QToolBar { background: #F5F5F5; border-bottom: 1px solid #E0E0E0; }
            QStatusBar { background: #F5F5F5; }
            QHeaderView::section { background-color: #F5F5F5; color: #616161; border: 1px solid #E0E0E0; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 3px; }
            QPushButton { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #FAFAFA; }
            """
        self.setStyleSheet(qss)

    def init_toolbar(self):
        tb = QToolBar("主工具栏", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, tb)

        # 标准图标
        st = self.style()
        icon_refresh = st.standardIcon(QStyle.SP_BrowserReload)
        icon_run = st.standardIcon(QStyle.SP_MediaPlay)
        icon_export = st.standardIcon(QStyle.SP_DialogSaveButton)
        icon_info = st.standardIcon(QStyle.SP_MessageBoxInformation)
        icon_theme = st.standardIcon(QStyle.SP_DialogHelpButton)

        act_fetch = QAction(icon_refresh, "获取全部股票", self)
        act_fetch.triggered.connect(self.on_fetch_data)
        act_fetch.setShortcut("Ctrl+R")
        tb.addAction(act_fetch)

        act_select = QAction(icon_run, "执行选股", self)
        act_select.triggered.connect(self.on_select_stock)
        act_select.setShortcut("F5")
        tb.addAction(act_select)

        act_export = QAction(icon_export, "导出选股结果", self)
        act_export.triggered.connect(self.on_export_excel)
        act_export.setShortcut("Ctrl+E")
        tb.addAction(act_export)

        tb.addSeparator()

        act_detail = QAction(icon_info, "查看详情", self)
        act_detail.triggered.connect(self.on_view_detail)
        act_detail.setShortcut("Enter")
        tb.addAction(act_detail)

        tb.addSeparator()

        act_bt_run = QAction(icon_run, "运行回测", self)
        act_bt_run.triggered.connect(self.on_run_backtest)
        act_bt_run.setShortcut("Ctrl+B")
        tb.addAction(act_bt_run)

        act_bt_export = QAction(icon_export, "导出回测明细", self)
        act_bt_export.triggered.connect(self.on_export_backtest)
        act_bt_export.setShortcut("Ctrl+Shift+E")
        tb.addAction(act_bt_export)

        tb.addSeparator()

        # 重置评分权重
        act_reset_weights = QAction("重置权重", self)
        act_reset_weights.triggered.connect(self.on_reset_weights)
        tb.addAction(act_reset_weights)

        # 主题切换
        act_theme = QAction(icon_theme, "切换主题", self)
        def _toggle_theme():
            self.apply_theme(dark=not self._dark_theme)
        act_theme.triggered.connect(_toggle_theme)
        act_theme.setShortcut("Ctrl+T")
        tb.addAction(act_theme)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索代码/名称  回车筛选/清空恢复")
        self.search_edit.returnPressed.connect(self.apply_table_search)
        wa = QWidgetAction(self)
        wa.setDefaultWidget(self.search_edit)
        tb.addAction(wa)

    def init_ui(self):
        # 主题与状态栏和 Dock 等已在上一段定义，这里继续原实现
        self.apply_theme(dark=True)
        self.setStatusBar(QStatusBar(self))
        self.info_label = QLabel("欢迎使用A股选股分析工具")
        self.statusBar().addPermanentWidget(self.info_label, 1)

        # =============== 左侧：筛选器（放入可滚动 Dock） ===============
        filters_container = QWidget()
        filters_layout = QVBoxLayout()
        filters_layout.setContentsMargins(8, 8, 8, 8)
        filters_layout.setSpacing(8)

        # --- 屏蔽前缀 ---
        block_group = QGroupBox("屏蔽股票前缀")
        block_layout = QHBoxLayout()
        self.prefix_checkboxes = []
        for prefix in ["30", "68", "4", "8"]:
            cb = QCheckBox(prefix)
            cb.setChecked(True)
            self.prefix_checkboxes.append(cb)
            block_layout.addWidget(cb)
        block_group.setLayout(block_layout)
        filters_layout.addWidget(block_group)

        # --- 日期区间 ---
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
        filters_layout.addWidget(date_group)

        # --- 涨幅筛选 ---
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
        self.single_days_spin = QSpinBox()
        self.single_days_spin.setRange(1, 365)
        self.single_days_spin.setValue(20)
        filter_layout.addWidget(QLabel("在最近N天内:"))
        filter_layout.addWidget(self.single_days_spin)
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)

        # --- 成交量策略 ---
        vol_group = QGroupBox("成交量")
        vol_layout = QHBoxLayout()
        self.volume_mode = QComboBox()
        self.volume_mode.addItems(["无", "放量突破", "缩量回调"])  # None | volume_breakout | volume_pullback
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
        vol_layout.addWidget(QLabel("回踩MA(N=0关闭):"))
        vol_layout.addWidget(self.touch_ma_spin)
        vol_group.setLayout(vol_layout)
        filters_layout.addWidget(vol_group)

        # --- 均线系统 ---
        ma_group = QGroupBox("均线系统")
        ma_layout = QHBoxLayout()
        self.ma_days_input = QLineEdit("5,10,20")
        self.ma_align_combo = QComboBox()
        self.ma_align_combo.addItems(["无", "多头", "空头"])  # None | long | short
        self.price_above_ma_spin = QSpinBox()
        self.price_above_ma_spin.setRange(0, 250)
        self.price_above_ma_spin.setValue(0)
        ma_layout.addWidget(QLabel("MA天数(逗号):"))
        ma_layout.addWidget(self.ma_days_input)
        ma_layout.addWidget(QLabel("排列:"))
        ma_layout.addWidget(self.ma_align_combo)
        ma_layout.addWidget(QLabel("价格在N日MA之上(0为关闭):"))
        ma_layout.addWidget(self.price_above_ma_spin)
        ma_group.setLayout(ma_layout)
        filters_layout.addWidget(ma_group)

        # --- 热度 ---
        heat_group = QGroupBox("热度(新闻条数)")
        heat_layout = QHBoxLayout()
        self.heat_min_news = QSpinBox()
        self.heat_min_news.setRange(0, 100000)
        self.heat_min_news.setValue(0)
        self.heat_window = QSpinBox()
        self.heat_window.setRange(1, 60)
        self.heat_window.setValue(5)
        heat_layout.addWidget(QLabel("最小新闻数:"))
        heat_layout.addWidget(self.heat_min_news)
        heat_layout.addWidget(QLabel("统计窗口N:"))
        heat_layout.addWidget(self.heat_window)
        heat_group.setLayout(heat_layout)
        filters_layout.addWidget(heat_group)

        # --- 技术条件 ---
        tech_group = QGroupBox("技术条件")
        tech_layout = QHBoxLayout()
        self.breakout_n_spin = QSpinBox()
        self.breakout_n_spin.setRange(0, 250)
        self.breakout_n_spin.setValue(0)
        self.breakout_min_pct = QLineEdit()
        self.breakout_min_pct.setPlaceholderText("突破最小幅度% 可空")
        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(0, 250)
        self.atr_period_spin.setValue(0)
        self.atr_max_pct = QLineEdit()
        self.atr_max_pct.setPlaceholderText("ATR/价 ≤ % 可空")
        self.cb_macd = QCheckBox("MACD")
        self.macd_rule = QComboBox()
        self.macd_rule.addItems(["hist>0", "dif>dea", "金叉"])
        self.cb_rsi = QCheckBox("RSI")
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(1, 250)
        self.rsi_period_spin.setValue(14)
        self.rsi_min = QLineEdit()
        self.rsi_min.setPlaceholderText("RSI≥ 可空")
        self.rsi_max = QLineEdit()
        self.rsi_max.setPlaceholderText("RSI≤ 可空")
        tech_layout.addWidget(QLabel("N日新高N:"))
        tech_layout.addWidget(self.breakout_n_spin)
        tech_layout.addWidget(QLabel("最小突破%:"))
        tech_layout.addWidget(self.breakout_min_pct)
        tech_layout.addWidget(QLabel("ATR周期:"))
        tech_layout.addWidget(self.atr_period_spin)
        tech_layout.addWidget(QLabel("ATR/价≤%:"))
        tech_layout.addWidget(self.atr_max_pct)
        tech_layout.addWidget(self.cb_macd)
        tech_layout.addWidget(self.macd_rule)
        tech_layout.addWidget(self.cb_rsi)
        tech_layout.addWidget(self.rsi_period_spin)
        tech_layout.addWidget(self.rsi_min)
        tech_layout.addWidget(self.rsi_max)
        tech_group.setLayout(tech_layout)
        filters_layout.addWidget(tech_group)

        # --- 板块 ---
        board_group = QGroupBox("板块")
        board_layout = QHBoxLayout()
        self.board_in_input = QLineEdit()
        self.board_in_input.setPlaceholderText("包含板块代码/名称，逗号分隔")
        self.board_out_input = QLineEdit()
        self.board_out_input.setPlaceholderText("排除板块代码/名称，逗号分隔")
        board_layout.addWidget(QLabel("包含:"))
        board_layout.addWidget(self.board_in_input)
        board_layout.addWidget(QLabel("排除:"))
        board_layout.addWidget(self.board_out_input)
        board_group.setLayout(board_layout)
        filters_layout.addWidget(board_group)

        # --- 形态 ---
        pattern_group = QGroupBox("K线形态")
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
        pattern_layout.addWidget(QLabel("检测最近N根:"))
        pattern_layout.addWidget(self.pattern_window_spin)
        pattern_group.setLayout(pattern_layout)
        filters_layout.addWidget(pattern_group)

        # --- 评分权重 ---
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
        filters_layout.addWidget(weight_group)

        # --- 回测配置 ---
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
        self.bt_entry_mode.addItems(["当日收盘买入", "次日开盘买入"])  # close | next_open
        self.bt_exit_mode = QComboBox()
        self.bt_exit_mode.addItems(["n日后收盘卖出", "n日后开盘卖出"])  # close | open
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
        bt_layout.addWidget(QLabel("每日TopK(0不限):"))
        bt_layout.addWidget(self.bt_topk)
        bt_layout.addWidget(self.bt_entry_mode)
        bt_layout.addWidget(self.bt_exit_mode)
        bt_layout.addWidget(self.bt_exclude_limit)
        bt_layout.addWidget(QLabel("涨停阈值%:"))
        bt_layout.addWidget(self.bt_limit_th)
        bt_group.setLayout(bt_layout)
        filters_layout.addWidget(bt_group)

        filters_layout.addStretch(1)
        filters_container.setLayout(filters_layout)
        scroll = QScrollArea()
        scroll.setWidget(filters_container)
        scroll.setWidgetResizable(True)
        self.left_dock = QDockWidget("筛选条件", self)
        self.left_dock.setWidget(scroll)
        self.left_dock.setObjectName("dock_filters")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

        # =============== 中央：结果表格 ===============
        central = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(8, 8, 8, 8)

        # 顶部快速提示与搜索条（工具栏中提供更合适，这里仅放表格）
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "行业", "收盘价", "区间涨幅", "单日最大涨幅", "单日最大跌幅", "通过明细", "评分", "未来5日收益%"])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        central_layout.addWidget(self.table)
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # =============== 右侧：详情面板 ===============
        self.detail_panel = QWidget()
        dlayout = QVBoxLayout()
        dlayout.setContentsMargins(8, 8, 8, 8)
        self.detail_title = QLabel("选中行详情")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        dlayout.addWidget(self.detail_title)
        dlayout.addWidget(self.detail_text, 1)
        self.detail_panel.setLayout(dlayout)
        self.right_dock = QDockWidget("详情", self)
        self.right_dock.setObjectName("dock_detail")
        self.right_dock.setWidget(self.detail_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        # =============== 顶部工具栏 ===============
        self.init_toolbar()

        # =============== 信号连接 ===============
        self.table.cellDoubleClicked.connect(self.on_plot_kline)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.radio_recent.toggled.connect(self.toggle_date_mode)
        self.radio_custom.toggled.connect(self.toggle_date_mode)
        self.btn_reset_weights.clicked.connect(self.on_reset_weights)

        # 还原窗口布局
        try:
            geo = self.settings.value("main/geometry")
            state = self.settings.value("main/state")
            if geo:
                self.restoreGeometry(geo)
            if state:
                self.restoreState(state)
        except Exception:
            pass

        # 初始信息
        self.set_info("准备就绪")

    # 主题样式
    def apply_theme(self, dark: bool = True):
        self._dark_theme = dark
        if dark:
            qss = """
            QWidget { background-color: #121212; color: #E0E0E0; }
            QGroupBox { border: 1px solid #2A2A2A; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #BDBDBD; }
            QToolBar { background: #1E1E1E; border-bottom: 1px solid #2A2A2A; }
            QStatusBar { background: #1E1E1E; }
            QTableWidget { gridline-color: #2A2A2A; }
            QHeaderView::section { background-color: #1E1E1E; color: #BDBDBD; border: 1px solid #2A2A2A; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 4px; padding: 3px; }
            QPushButton { background: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #383838; }
            QDockWidget::title { text-align: left; padding-left: 6px; }
            QScrollBar:vertical { background: #1A1A1A; width: 10px; }
            QScrollBar::handle:vertical { background: #3A3A3A; min-height: 30px; border-radius: 4px; }
            """
        else:
            qss = """
            QWidget { background-color: #FAFAFA; color: #212121; }
            QGroupBox { border: 1px solid #DDDDDD; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #616161; }
            QToolBar { background: #F5F5F5; border-bottom: 1px solid #E0E0E0; }
            QStatusBar { background: #F5F5F5; }
            QHeaderView::section { background-color: #F5F5F5; color: #616161; border: 1px solid #E0E0E0; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 3px; }
            QPushButton { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #FAFAFA; }
            """
        self.setStyleSheet(qss)

    def init_toolbar(self):
        tb = QToolBar("主工具栏", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, tb)

        # 标准图标
        st = self.style()
        icon_refresh = st.standardIcon(QStyle.SP_BrowserReload)
        icon_run = st.standardIcon(QStyle.SP_MediaPlay)
        icon_export = st.standardIcon(QStyle.SP_DialogSaveButton)
        icon_info = st.standardIcon(QStyle.SP_MessageBoxInformation)
        icon_theme = st.standardIcon(QStyle.SP_DialogHelpButton)

        act_fetch = QAction(icon_refresh, "获取全部股票", self)
        act_fetch.triggered.connect(self.on_fetch_data)
        act_fetch.setShortcut("Ctrl+R")
        tb.addAction(act_fetch)

        act_select = QAction(icon_run, "执行选股", self)
        act_select.triggered.connect(self.on_select_stock)
        act_select.setShortcut("F5")
        tb.addAction(act_select)

        act_export = QAction(icon_export, "导出选股结果", self)
        act_export.triggered.connect(self.on_export_excel)
        act_export.setShortcut("Ctrl+E")
        tb.addAction(act_export)

        tb.addSeparator()

        act_detail = QAction(icon_info, "查看详情", self)
        act_detail.triggered.connect(self.on_view_detail)
        act_detail.setShortcut("Enter")
        tb.addAction(act_detail)

        tb.addSeparator()

        act_bt_run = QAction(icon_run, "运行回测", self)
        act_bt_run.triggered.connect(self.on_run_backtest)
        act_bt_run.setShortcut("Ctrl+B")
        tb.addAction(act_bt_run)

        act_bt_export = QAction(icon_export, "导出回测明细", self)
        act_bt_export.triggered.connect(self.on_export_backtest)
        act_bt_export.setShortcut("Ctrl+Shift+E")
        tb.addAction(act_bt_export)

        tb.addSeparator()

        # 重置评分权重
        act_reset_weights = QAction("重置权重", self)
        act_reset_weights.triggered.connect(self.on_reset_weights)
        tb.addAction(act_reset_weights)

        # 主题切换
        act_theme = QAction(icon_theme, "切换主题", self)
        def _toggle_theme():
            self.apply_theme(dark=not self._dark_theme)
        act_theme.triggered.connect(_toggle_theme)
        act_theme.setShortcut("Ctrl+T")
        tb.addAction(act_theme)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索代码/名称  回车筛选/清空恢复")
        self.search_edit.returnPressed.connect(self.apply_table_search)
        wa = QWidgetAction(self)
        wa.setDefaultWidget(self.search_edit)
        tb.addAction(wa)

    def init_ui(self):
        # 主题与状态栏和 Dock 等已在上一段定义，这里继续原实现
        self.apply_theme(dark=True)
        self.setStatusBar(QStatusBar(self))
        self.info_label = QLabel("欢迎使用A股选股分析工具")
        self.statusBar().addPermanentWidget(self.info_label, 1)

        # =============== 左侧：筛选器（放入可滚动 Dock） ===============
        filters_container = QWidget()
        filters_layout = QVBoxLayout()
        filters_layout.setContentsMargins(8, 8, 8, 8)
        filters_layout.setSpacing(8)

        # --- 屏蔽前缀 ---
        block_group = QGroupBox("屏蔽股票前缀")
        block_layout = QHBoxLayout()
        self.prefix_checkboxes = []
        for prefix in ["30", "68", "4", "8"]:
            cb = QCheckBox(prefix)
            cb.setChecked(True)
            self.prefix_checkboxes.append(cb)
            block_layout.addWidget(cb)
        block_group.setLayout(block_layout)
        filters_layout.addWidget(block_group)

        # --- 日期区间 ---
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
        filters_layout.addWidget(date_group)

        # --- 涨幅筛选 ---
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
        self.single_days_spin = QSpinBox()
        self.single_days_spin.setRange(1, 365)
        self.single_days_spin.setValue(20)
        filter_layout.addWidget(QLabel("在最近N天内:"))
        filter_layout.addWidget(self.single_days_spin)
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)

        # --- 成交量策略 ---
        vol_group = QGroupBox("成交量")
        vol_layout = QHBoxLayout()
        self.volume_mode = QComboBox()
        self.volume_mode.addItems(["无", "放量突破", "缩量回调"])  # None | volume_breakout | volume_pullback
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
        vol_layout.addWidget(QLabel("回踩MA(N=0关闭):"))
        vol_layout.addWidget(self.touch_ma_spin)
        vol_group.setLayout(vol_layout)
        filters_layout.addWidget(vol_group)

        # --- 均线系统 ---
        ma_group = QGroupBox("均线系统")
        ma_layout = QHBoxLayout()
        self.ma_days_input = QLineEdit("5,10,20")
        self.ma_align_combo = QComboBox()
        self.ma_align_combo.addItems(["无", "多头", "空头"])  # None | long | short
        self.price_above_ma_spin = QSpinBox()
        self.price_above_ma_spin.setRange(0, 250)
        self.price_above_ma_spin.setValue(0)
        ma_layout.addWidget(QLabel("MA天数(逗号):"))
        ma_layout.addWidget(self.ma_days_input)
        ma_layout.addWidget(QLabel("排列:"))
        ma_layout.addWidget(self.ma_align_combo)
        ma_layout.addWidget(QLabel("价格在N日MA之上(0为关闭):"))
        ma_layout.addWidget(self.price_above_ma_spin)
        ma_group.setLayout(ma_layout)
        filters_layout.addWidget(ma_group)

        # --- 热度 ---
        heat_group = QGroupBox("热度(新闻条数)")
        heat_layout = QHBoxLayout()
        self.heat_min_news = QSpinBox()
        self.heat_min_news.setRange(0, 100000)
        self.heat_min_news.setValue(0)
        self.heat_window = QSpinBox()
        self.heat_window.setRange(1, 60)
        self.heat_window.setValue(5)
        heat_layout.addWidget(QLabel("最小新闻数:"))
        heat_layout.addWidget(self.heat_min_news)
        heat_layout.addWidget(QLabel("统计窗口N:"))
        heat_layout.addWidget(self.heat_window)
        heat_group.setLayout(heat_layout)
        filters_layout.addWidget(heat_group)

        # --- 技术条件 ---
        tech_group = QGroupBox("技术条件")
        tech_layout = QHBoxLayout()
        self.breakout_n_spin = QSpinBox()
        self.breakout_n_spin.setRange(0, 250)
        self.breakout_n_spin.setValue(0)
        self.breakout_min_pct = QLineEdit()
        self.breakout_min_pct.setPlaceholderText("突破最小幅度% 可空")
        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(0, 250)
        self.atr_period_spin.setValue(0)
        self.atr_max_pct = QLineEdit()
        self.atr_max_pct.setPlaceholderText("ATR/价 ≤ % 可空")
        self.cb_macd = QCheckBox("MACD")
        self.macd_rule = QComboBox()
        self.macd_rule.addItems(["hist>0", "dif>dea", "金叉"])
        self.cb_rsi = QCheckBox("RSI")
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(1, 250)
        self.rsi_period_spin.setValue(14)
        self.rsi_min = QLineEdit()
        self.rsi_min.setPlaceholderText("RSI≥ 可空")
        self.rsi_max = QLineEdit()
        self.rsi_max.setPlaceholderText("RSI≤ 可空")
        tech_layout.addWidget(QLabel("N日新高N:"))
        tech_layout.addWidget(self.breakout_n_spin)
        tech_layout.addWidget(QLabel("最小突破%:"))
        tech_layout.addWidget(self.breakout_min_pct)
        tech_layout.addWidget(QLabel("ATR周期:"))
        tech_layout.addWidget(self.atr_period_spin)
        tech_layout.addWidget(QLabel("ATR/价≤%:"))
        tech_layout.addWidget(self.atr_max_pct)
        tech_layout.addWidget(self.cb_macd)
        tech_layout.addWidget(self.macd_rule)
        tech_layout.addWidget(self.cb_rsi)
        tech_layout.addWidget(self.rsi_period_spin)
        tech_layout.addWidget(self.rsi_min)
        tech_layout.addWidget(self.rsi_max)
        tech_group.setLayout(tech_layout)
        filters_layout.addWidget(tech_group)

        # --- 板块 ---
        board_group = QGroupBox("板块")
        board_layout = QHBoxLayout()
        self.board_in_input = QLineEdit()
        self.board_in_input.setPlaceholderText("包含板块代码/名称，逗号分隔")
        self.board_out_input = QLineEdit()
        self.board_out_input.setPlaceholderText("排除板块代码/名称，逗号分隔")
        board_layout.addWidget(QLabel("包含:"))
        board_layout.addWidget(self.board_in_input)
        board_layout.addWidget(QLabel("排除:"))
        board_layout.addWidget(self.board_out_input)
        board_group.setLayout(board_layout)
        filters_layout.addWidget(board_group)

        # --- 形态 ---
        pattern_group = QGroupBox("K线形态")
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
        pattern_layout.addWidget(QLabel("检测最近N根:"))
        pattern_layout.addWidget(self.pattern_window_spin)
        pattern_group.setLayout(pattern_layout)
        filters_layout.addWidget(pattern_group)

        # --- 评分权重 ---
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
        filters_layout.addWidget(weight_group)

        # --- 回测配置 ---
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
        self.bt_entry_mode.addItems(["当日收盘买入", "次日开盘买入"])  # close | next_open
        self.bt_exit_mode = QComboBox()
        self.bt_exit_mode.addItems(["n日后收盘卖出", "n日后开盘卖出"])  # close | open
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
        bt_layout.addWidget(QLabel("每日TopK(0不限):"))
        bt_layout.addWidget(self.bt_topk)
        bt_layout.addWidget(self.bt_entry_mode)
        bt_layout.addWidget(self.bt_exit_mode)
        bt_layout.addWidget(self.bt_exclude_limit)
        bt_layout.addWidget(QLabel("涨停阈值%:"))
        bt_layout.addWidget(self.bt_limit_th)
        bt_group.setLayout(bt_layout)
        filters_layout.addWidget(bt_group)

        filters_layout.addStretch(1)
        filters_container.setLayout(filters_layout)
        scroll = QScrollArea()
        scroll.setWidget(filters_container)
        scroll.setWidgetResizable(True)
        self.left_dock = QDockWidget("筛选条件", self)
        self.left_dock.setWidget(scroll)
        self.left_dock.setObjectName("dock_filters")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

        # =============== 中央：结果表格 ===============
        central = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(8, 8, 8, 8)

        # 顶部快速提示与搜索条（工具栏中提供更合适，这里仅放表格）
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "行业", "收盘价", "区间涨幅", "单日最大涨幅", "单日最大跌幅", "通过明细", "评分", "未来5日收益%"])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        central_layout.addWidget(self.table)
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # =============== 右侧：详情面板 ===============
        self.detail_panel = QWidget()
        dlayout = QVBoxLayout()
        dlayout.setContentsMargins(8, 8, 8, 8)
        self.detail_title = QLabel("选中行详情")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        dlayout.addWidget(self.detail_title)
        dlayout.addWidget(self.detail_text, 1)
        self.detail_panel.setLayout(dlayout)
        self.right_dock = QDockWidget("详情", self)
        self.right_dock.setObjectName("dock_detail")
        self.right_dock.setWidget(self.detail_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        # =============== 顶部工具栏 ===============
        self.init_toolbar()

        # =============== 信号连接 ===============
        self.table.cellDoubleClicked.connect(self.on_plot_kline)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.radio_recent.toggled.connect(self.toggle_date_mode)
        self.radio_custom.toggled.connect(self.toggle_date_mode)
        self.btn_reset_weights.clicked.connect(self.on_reset_weights)

        # 还原窗口布局
        try:
            geo = self.settings.value("main/geometry")
            state = self.settings.value("main/state")
            if geo:
                self.restoreGeometry(geo)
            if state:
                self.restoreState(state)
        except Exception:
            pass

        # 初始信息
        self.set_info("准备就绪")

    # 主题样式
    def apply_theme(self, dark: bool = True):
        self._dark_theme = dark
        if dark:
            qss = """
            QWidget { background-color: #121212; color: #E0E0E0; }
            QGroupBox { border: 1px solid #2A2A2A; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #BDBDBD; }
            QToolBar { background: #1E1E1E; border-bottom: 1px solid #2A2A2A; }
            QStatusBar { background: #1E1E1E; }
            QTableWidget { gridline-color: #2A2A2A; }
            QHeaderView::section { background-color: #1E1E1E; color: #BDBDBD; border: 1px solid #2A2A2A; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 4px; padding: 3px; }
            QPushButton { background: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #383838; }
            QDockWidget::title { text-align: left; padding-left: 6px; }
            QScrollBar:vertical { background: #1A1A1A; width: 10px; }
            QScrollBar::handle:vertical { background: #3A3A3A; min-height: 30px; border-radius: 4px; }
            """
        else:
            qss = """
            QWidget { background-color: #FAFAFA; color: #212121; }
            QGroupBox { border: 1px solid #DDDDDD; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #616161; }
            QToolBar { background: #F5F5F5; border-bottom: 1px solid #E0E0E0; }
            QStatusBar { background: #F5F5F5; }
            QHeaderView::section { background-color: #F5F5F5; color: #616161; border: 1px solid #E0E0E0; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 3px; }
            QPushButton { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #FAFAFA; }
            """
        self.setStyleSheet(qss)

    def init_toolbar(self):
        tb = QToolBar("主工具栏", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, tb)

        # 标准图标
        st = self.style()
        icon_refresh = st.standardIcon(QStyle.SP_BrowserReload)
        icon_run = st.standardIcon(QStyle.SP_MediaPlay)
        icon_export = st.standardIcon(QStyle.SP_DialogSaveButton)
        icon_info = st.standardIcon(QStyle.SP_MessageBoxInformation)
        icon_theme = st.standardIcon(QStyle.SP_DialogHelpButton)

        act_fetch = QAction(icon_refresh, "获取全部股票", self)
        act_fetch.triggered.connect(self.on_fetch_data)
        act_fetch.setShortcut("Ctrl+R")
        tb.addAction(act_fetch)

        act_select = QAction(icon_run, "执行选股", self)
        act_select.triggered.connect(self.on_select_stock)
        act_select.setShortcut("F5")
        tb.addAction(act_select)

        act_export = QAction(icon_export, "导出选股结果", self)
        act_export.triggered.connect(self.on_export_excel)
        act_export.setShortcut("Ctrl+E")
        tb.addAction(act_export)

        tb.addSeparator()

        act_detail = QAction(icon_info, "查看详情", self)
        act_detail.triggered.connect(self.on_view_detail)
        act_detail.setShortcut("Enter")
        tb.addAction(act_detail)

        tb.addSeparator()

        act_bt_run = QAction(icon_run, "运行回测", self)
        act_bt_run.triggered.connect(self.on_run_backtest)
        act_bt_run.setShortcut("Ctrl+B")
        tb.addAction(act_bt_run)

        act_bt_export = QAction(icon_export, "导出回测明细", self)
        act_bt_export.triggered.connect(self.on_export_backtest)
        act_bt_export.setShortcut("Ctrl+Shift+E")
        tb.addAction(act_bt_export)

        tb.addSeparator()

        # 重置评分权重
        act_reset_weights = QAction("重置权重", self)
        act_reset_weights.triggered.connect(self.on_reset_weights)
        tb.addAction(act_reset_weights)

        # 主题切换
        act_theme = QAction(icon_theme, "切换主题", self)
        def _toggle_theme():
            self.apply_theme(dark=not self._dark_theme)
        act_theme.triggered.connect(_toggle_theme)
        act_theme.setShortcut("Ctrl+T")
        tb.addAction(act_theme)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索代码/名称  回车筛选/清空恢复")
        self.search_edit.returnPressed.connect(self.apply_table_search)
        wa = QWidgetAction(self)
        wa.setDefaultWidget(self.search_edit)
        tb.addAction(wa)

    def init_ui(self):
        # 主题与状态栏和 Dock 等已在上一段定义，这里继续原实现
        self.apply_theme(dark=True)
        self.setStatusBar(QStatusBar(self))
        self.info_label = QLabel("欢迎使用A股选股分析工具")
        self.statusBar().addPermanentWidget(self.info_label, 1)

        # =============== 左侧：筛选器（放入可滚动 Dock） ===============
        filters_container = QWidget()
        filters_layout = QVBoxLayout()
        filters_layout.setContentsMargins(8, 8, 8, 8)
        filters_layout.setSpacing(8)

        # --- 屏蔽前缀 ---
        block_group = QGroupBox("屏蔽股票前缀")
        block_layout = QHBoxLayout()
        self.prefix_checkboxes = []
        for prefix in ["30", "68", "4", "8"]:
            cb = QCheckBox(prefix)
            cb.setChecked(True)
            self.prefix_checkboxes.append(cb)
            block_layout.addWidget(cb)
        block_group.setLayout(block_layout)
        filters_layout.addWidget(block_group)

        # --- 日期区间 ---
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
        filters_layout.addWidget(date_group)

        # --- 涨幅筛选 ---
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
        self.single_days_spin = QSpinBox()
        self.single_days_spin.setRange(1, 365)
        self.single_days_spin.setValue(20)
        filter_layout.addWidget(QLabel("在最近N天内:"))
        filter_layout.addWidget(self.single_days_spin)
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)

        # --- 成交量策略 ---
        vol_group = QGroupBox("成交量")
        vol_layout = QHBoxLayout()
        self.volume_mode = QComboBox()
        self.volume_mode.addItems(["无", "放量突破", "缩量回调"])  # None | volume_breakout | volume_pullback
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
        vol_layout.addWidget(QLabel("回踩MA(N=0关闭):"))
        vol_layout.addWidget(self.touch_ma_spin)
        vol_group.setLayout(vol_layout)
        filters_layout.addWidget(vol_group)

        # --- 均线系统 ---
        ma_group = QGroupBox("均线系统")
        ma_layout = QHBoxLayout()
        self.ma_days_input = QLineEdit("5,10,20")
        self.ma_align_combo = QComboBox()
        self.ma_align_combo.addItems(["无", "多头", "空头"])  # None | long | short
        self.price_above_ma_spin = QSpinBox()
        self.price_above_ma_spin.setRange(0, 250)
        self.price_above_ma_spin.setValue(0)
        ma_layout.addWidget(QLabel("MA天数(逗号):"))
        ma_layout.addWidget(self.ma_days_input)
        ma_layout.addWidget(QLabel("排列:"))
        ma_layout.addWidget(self.ma_align_combo)
        ma_layout.addWidget(QLabel("价格在N日MA之上(0为关闭):"))
        ma_layout.addWidget(self.price_above_ma_spin)
        ma_group.setLayout(ma_layout)
        filters_layout.addWidget(ma_group)

        # --- 热度 ---
        heat_group = QGroupBox("热度(新闻条数)")
        heat_layout = QHBoxLayout()
        self.heat_min_news = QSpinBox()
        self.heat_min_news.setRange(0, 100000)
        self.heat_min_news.setValue(0)
        self.heat_window = QSpinBox()
        self.heat_window.setRange(1, 60)
        self.heat_window.setValue(5)
        heat_layout.addWidget(QLabel("最小新闻数:"))
        heat_layout.addWidget(self.heat_min_news)
        heat_layout.addWidget(QLabel("统计窗口N:"))
        heat_layout.addWidget(self.heat_window)
        heat_group.setLayout(heat_layout)
        filters_layout.addWidget(heat_group)

        # --- 技术条件 ---
        tech_group = QGroupBox("技术条件")
        tech_layout = QHBoxLayout()
        self.breakout_n_spin = QSpinBox()
        self.breakout_n_spin.setRange(0, 250)
        self.breakout_n_spin.setValue(0)
        self.breakout_min_pct = QLineEdit()
        self.breakout_min_pct.setPlaceholderText("突破最小幅度% 可空")
        self.atr_period_spin = QSpinBox()
        self.atr_period_spin.setRange(0, 250)
        self.atr_period_spin.setValue(0)
        self.atr_max_pct = QLineEdit()
        self.atr_max_pct.setPlaceholderText("ATR/价 ≤ % 可空")
        self.cb_macd = QCheckBox("MACD")
        self.macd_rule = QComboBox()
        self.macd_rule.addItems(["hist>0", "dif>dea", "金叉"])
        self.cb_rsi = QCheckBox("RSI")
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(1, 250)
        self.rsi_period_spin.setValue(14)
        self.rsi_min = QLineEdit()
        self.rsi_min.setPlaceholderText("RSI≥ 可空")
        self.rsi_max = QLineEdit()
        self.rsi_max.setPlaceholderText("RSI≤ 可空")
        tech_layout.addWidget(QLabel("N日新高N:"))
        tech_layout.addWidget(self.breakout_n_spin)
        tech_layout.addWidget(QLabel("最小突破%:"))
        tech_layout.addWidget(self.breakout_min_pct)
        tech_layout.addWidget(QLabel("ATR周期:"))
        tech_layout.addWidget(self.atr_period_spin)
        tech_layout.addWidget(QLabel("ATR/价≤%:"))
        tech_layout.addWidget(self.atr_max_pct)
        tech_layout.addWidget(self.cb_macd)
        tech_layout.addWidget(self.macd_rule)
        tech_layout.addWidget(self.cb_rsi)
        tech_layout.addWidget(self.rsi_period_spin)
        tech_layout.addWidget(self.rsi_min)
        tech_layout.addWidget(self.rsi_max)
        tech_group.setLayout(tech_layout)
        filters_layout.addWidget(tech_group)

        # --- 板块 ---
        board_group = QGroupBox("板块")
        board_layout = QHBoxLayout()
        self.board_in_input = QLineEdit()
        self.board_in_input.setPlaceholderText("包含板块代码/名称，逗号分隔")
        self.board_out_input = QLineEdit()
        self.board_out_input.setPlaceholderText("排除板块代码/名称，逗号分隔")
        board_layout.addWidget(QLabel("包含:"))
        board_layout.addWidget(self.board_in_input)
        board_layout.addWidget(QLabel("排除:"))
        board_layout.addWidget(self.board_out_input)
        board_group.setLayout(board_layout)
        filters_layout.addWidget(board_group)

        # --- 形态 ---
        pattern_group = QGroupBox("K线形态")
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
        pattern_layout.addWidget(QLabel("检测最近N根:"))
        pattern_layout.addWidget(self.pattern_window_spin)
        pattern_group.setLayout(pattern_layout)
        filters_layout.addWidget(pattern_group)

        # --- 评分权重 ---
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
        filters_layout.addWidget(weight_group)

        # --- 回测配置 ---
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
        self.bt_entry_mode.addItems(["当日收盘买入", "次日开盘买入"])  # close | next_open
        self.bt_exit_mode = QComboBox()
        self.bt_exit_mode.addItems(["n日后收盘卖出", "n日后开盘卖出"])  # close | open
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
        bt_layout.addWidget(QLabel("每日TopK(0不限):"))
        bt_layout.addWidget(self.bt_topk)
        bt_layout.addWidget(self.bt_entry_mode)
        bt_layout.addWidget(self.bt_exit_mode)
        bt_layout.addWidget(self.bt_exclude_limit)
        bt_layout.addWidget(QLabel("涨停阈值%:"))
        bt_layout.addWidget(self.bt_limit_th)
        bt_group.setLayout(bt_layout)
        filters_layout.addWidget(bt_group)

        filters_layout.addStretch(1)
        filters_container.setLayout(filters_layout)
        scroll = QScrollArea()
        scroll.setWidget(filters_container)
        scroll.setWidgetResizable(True)
        self.left_dock = QDockWidget("筛选条件", self)
        self.left_dock.setWidget(scroll)
        self.left_dock.setObjectName("dock_filters")
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

        # =============== 中央：结果表格 ===============
        central = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(8, 8, 8, 8)

        # 顶部快速提示与搜索条（工具栏中提供更合适，这里仅放表格）
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["代码", "名称", "行业", "收盘价", "区间涨幅", "单日最大涨幅", "单日最大跌幅", "通过明细", "评分", "未来5日收益%"])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        central_layout.addWidget(self.table)
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # =============== 右侧：详情面板 ===============
        self.detail_panel = QWidget()
        dlayout = QVBoxLayout()
        dlayout.setContentsMargins(8, 8, 8, 8)
        self.detail_title = QLabel("选中行详情")
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        dlayout.addWidget(self.detail_title)
        dlayout.addWidget(self.detail_text, 1)
        self.detail_panel.setLayout(dlayout)
        self.right_dock = QDockWidget("详情", self)
        self.right_dock.setObjectName("dock_detail")
        self.right_dock.setWidget(self.detail_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        # =============== 顶部工具栏 ===============
        self.init_toolbar()

        # =============== 信号连接 ===============
        self.table.cellDoubleClicked.connect(self.on_plot_kline)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.radio_recent.toggled.connect(self.toggle_date_mode)
        self.radio_custom.toggled.connect(self.toggle_date_mode)
        self.btn_reset_weights.clicked.connect(self.on_reset_weights)

        # 还原窗口布局
        try:
            geo = self.settings.value("main/geometry")
            state = self.settings.value("main/state")
            if geo:
                self.restoreGeometry(geo)
            if state:
                self.restoreState(state)
        except Exception:
            pass

        # 初始信息
        self.set_info("准备就绪")

    # 主题样式
    def apply_theme(self, dark: bool = True):
        self._dark_theme = dark
        if dark:
            qss = """
            QWidget { background-color: #121212; color: #E0E0E0; }
            QGroupBox { border: 1px solid #2A2A2A; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #BDBDBD; }
            QToolBar { background: #1E1E1E; border-bottom: 1px solid #2A2A2A; }
            QStatusBar { background: #1E1E1E; }
            QTableWidget { gridline-color: #2A2A2A; }
            QHeaderView::section { background-color: #1E1E1E; color: #BDBDBD; border: 1px solid #2A2A2A; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #1A1A1A; border: 1px solid #2A2A2A; border-radius: 4px; padding: 3px; }
            QPushButton { background: #2D2D2D; border: 1px solid #3A3A3A; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #383838; }
            QDockWidget::title { text-align: left; padding-left: 6px; }
            QScrollBar:vertical { background: #1A1A1A; width: 10px; }
            QScrollBar::handle:vertical { background: #3A3A3A; min-height: 30px; border-radius: 4px; }
            """
        else:
            qss = """
            QWidget { background-color: #FAFAFA; color: #212121; }
            QGroupBox { border: 1px solid #DDDDDD; margin-top: 8px; border-radius: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #616161; }
            QToolBar { background: #F5F5F5; border-bottom: 1px solid #E0E0E0; }
            QStatusBar { background: #F5F5F5; }
            QHeaderView::section { background-color: #F5F5F5; color: #616161; border: 1px solid #E0E0E0; padding: 4px; }
            QLineEdit, QSpinBox, QComboBox, QTextEdit { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 3px; }
            QPushButton { background: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 5px 10px; }
            QPushButton:hover { background: #FAFAFA; }
            """
        self.setStyleSheet(qss)

    def init_toolbar(self):
        tb = QToolBar("主工具栏", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(Qt.TopToolBarArea, tb)

        # 标准图标
        st = self.style()
        icon_refresh = st.standardIcon(QStyle.SP_BrowserReload)
        icon_run = st.standardIcon(QStyle.SP_MediaPlay)
        icon_export = st.standardIcon(QStyle.SP_DialogSaveButton)
        icon_info = st.standardIcon(QStyle.SP_MessageBoxInformation)
        icon_theme = st.standardIcon(QStyle.SP_DialogHelpButton)

        act_fetch = QAction(icon_refresh, "获取全部股票", self)
        act_fetch.triggered.connect(self.on_fetch_data)
        act_fetch.setShortcut("Ctrl+R")
        tb.addAction(act_fetch)

        act_select = QAction(icon_run, "执行选股", self)
        act_select.triggered.connect(self.on_select_stock)
        act_select.setShortcut("F5")
        tb.addAction(act_select)

        act_export = QAction(icon_export, "导出选股结果", self)
        act_export.triggered.connect(self.on_export_excel)
        act_export.setShortcut("Ctrl+E")
        tb.addAction(act_export)

        tb.addSeparator()

        act_detail = QAction(icon_info, "查看详情", self)
        act_detail.triggered.connect(self.on_view_detail)
        act_detail.setShortcut("Enter")
        tb.addAction(act_detail)

        tb.addSeparator()

        act_bt_run = QAction(icon_run, "运行回测", self)
        act_bt_run.triggered.connect(self.on_run_backtest)
        act_bt_run.setShortcut("Ctrl+B")
        tb.addAction(act_bt_run)

        act_bt_export = QAction(icon_export, "导出回测明细", self)
        act_bt_export.triggered.connect(self.on_export_backtest)
        act_bt_export.setShortcut("Ctrl+Shift+E")
        tb.addAction(act_bt_export)

        tb.addSeparator()

        # 重置评分权重
        act_reset_weights = QAction("重置权重", self)
        act_reset_weights.triggered.connect(self.on_reset_weights)
        tb.addAction(act_reset_weights)

        # 主题切换
        act_theme = QAction(icon_theme, "切换主题", self)
        def _toggle_theme():
            self.apply_theme(dark=not self._dark_theme)
        act_theme.triggered.connect(_toggle_theme)
        act_theme.setShortcut("Ctrl+T")
        tb.addAction(act_theme)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索代码/名称  回车筛选/清空恢复")
        self.search_edit.returnPressed.connect(self.apply_table_search)
        wa = QWidgetAction(self)
        wa.setDefaultWidget(self.search_edit)
        tb.addAction(wa)

    def init_ui(self):
        # 主题与状态栏和 Dock 等已在上一段定义，这里继续原实现
        self.apply_theme(dark=True)
        self.setStatusBar(QStatusBar(self))
        self.info_label = QLabel("欢迎使用A股选股分析工具")
        self.statusBar().addPermanentWidget(self.info_label, 1)

        # =============== 左侧：筛选器（放入可滚动 Dock） ===============