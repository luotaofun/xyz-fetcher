# SPDX-License-Identifier: MIT
"""PyQt6 desktop interface for XYZ Fetcher."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QCloseEvent, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui_app.backend import (
    DEFAULT_CONFIG,
    PROJECT_ROOT,
    Repository,
    TaskManager,
    TaskOptions,
    episode_srt,
    export_episode,
    export_episode_csv,
    format_duration,
    format_ms,
    parse_target,
    run_async,
)
from gui_app.theme import DANGER, MUTED, STYLE, SUCCESS, WARNING


def card_layout() -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("Card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(12)
    return card, layout


def page_header(title: str, subtitle: str) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(3)
    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setProperty("muted", True)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    return layout


def empty_state(title: str, subtitle: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.addStretch(1)
    title_label = QLabel(title)
    title_label.setObjectName("EmptyTitle")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("EmptySubtitle")
    subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    layout.addStretch(1)
    return widget


def selectable_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def card_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("CardTitle")
    return label


def meta_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Meta")
    label.setWordWrap(True)
    return label


def status_pill(text: str, state: str = "neutral") -> QLabel:
    label = QLabel(text)
    label.setObjectName("StatusPill")
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    set_status_pill(label, text, state)
    return label


def set_status_pill(label: QLabel, text: str, state: str):
    label.setText(text)
    label.setProperty("state", state)
    label.style().unpolish(label)
    label.style().polish(label)


def nav_icon(name: str) -> QIcon:
    return QIcon(str(PROJECT_ROOT / "src" / "gui_app" / "assets" / f"{name}.svg"))


class FetchPage(QWidget):
    def __init__(self, tasks: TaskManager):
        super().__init__()
        self.tasks = tasks
        self.selected_task_id: str | None = None
        self._build_ui()
        self.tasks.tasks_changed.connect(self.refresh_tasks)
        self.tasks.task_output.connect(self.append_output)
        self.tasks.active_changed.connect(self.update_active)
        self.refresh_tasks()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)
        root.addLayout(page_header("抓取任务", "粘贴小宇宙链接，配置范围后加入后台队列"))

        form_card, form = card_layout()
        target_row = QHBoxLayout()
        target_row.setSpacing(12)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "粘贴小宇宙播客或单期链接，按 Enter 加入队列"
        )
        self.url_input.setClearButtonEnabled(True)
        self.url_input.returnPressed.connect(self.submit)
        self.submit_button = QPushButton("加入队列")
        self.submit_button.setObjectName("PrimaryButton")
        self.submit_button.clicked.connect(self.submit)
        target_row.addWidget(self.url_input, 1)
        target_row.addWidget(self.submit_button)
        form.addLayout(target_row)

        options_row = QHBoxLayout()
        options_row.setSpacing(14)
        self.transcripts_check = QCheckBox("抓取逐字稿")
        self.transcripts_check.setChecked(True)
        options_row.addWidget(self.transcripts_check)
        options_row.addWidget(QLabel("评论范围"))
        self.comments_combo = QComboBox()
        self.comments_combo.addItem("不抓评论", "none")
        self.comments_combo.addItem("仅最新一期", "latest")
        self.comments_combo.addItem("所有节目", "all")
        self.comments_combo.setCurrentIndex(1)
        options_row.addWidget(self.comments_combo)
        options_row.addWidget(QLabel("最多期数"))
        self.max_count = QSpinBox()
        self.max_count.setRange(0, 99999)
        self.max_count.setSpecialValueText("全部")
        self.max_count.setToolTip("0 表示全部；按整页生效，每页最多 20 条")
        options_row.addWidget(self.max_count)
        options_row.addStretch(1)
        self.target_badge = QLabel("支持播客和单期链接")
        self.target_badge.setObjectName("TargetBadge")
        options_row.addWidget(self.target_badge)
        form.addLayout(options_row)
        root.addWidget(form_card)

        active_row = QHBoxLayout()
        active_row.setContentsMargins(2, 0, 2, 0)
        self.active_pill = status_pill("队列空闲", "neutral")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFixedWidth(180)
        self.progress.setVisible(False)
        active_row.addWidget(self.active_pill)
        active_row.addStretch(1)
        active_row.addWidget(self.progress)
        root.addLayout(active_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        task_panel, task_layout = card_layout()
        task_header = QHBoxLayout()
        self.queue_title = card_title("任务队列")
        task_header.addWidget(self.queue_title)
        task_header.addStretch(1)
        self.cancel_button = QPushButton("取消所选")
        self.cancel_button.setObjectName("DangerButton")
        self.cancel_button.clicked.connect(self.cancel_selected)
        self.clear_button = QPushButton("清除已结束")
        self.clear_button.clicked.connect(self.tasks.clear_finished)
        task_header.addWidget(self.cancel_button)
        task_header.addWidget(self.clear_button)
        task_layout.addLayout(task_header)
        self.task_tree = QTreeWidget()
        self.task_tree.setHeaderLabels(["任务", "目标 ID", "状态"])
        self.task_tree.setRootIsDecorated(False)
        self.task_tree.setAlternatingRowColors(True)
        self.task_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.task_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.task_tree.itemSelectionChanged.connect(self.select_task)
        self.task_stack = QStackedWidget()
        self.task_stack.addWidget(empty_state("暂无抓取任务", "从上方粘贴链接开始，任务会按顺序执行"))
        self.task_stack.addWidget(self.task_tree)
        task_layout.addWidget(self.task_stack)
        splitter.addWidget(task_panel)

        log_panel, log_layout = card_layout()
        log_title = card_title("实时日志")
        log_layout.addWidget(log_title)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("任务输出会实时显示在这里")
        self.log_stack = QStackedWidget()
        self.log_stack.addWidget(empty_state("尚未选择任务", "选择左侧任务查看日志；运行中的任务会持续输出进度"))
        self.log_stack.addWidget(self.log_view)
        log_layout.addWidget(self.log_stack)
        splitter.addWidget(log_panel)
        splitter.setSizes([430, 650])
        root.addWidget(splitter, 1)

        self.url_input.textChanged.connect(self.update_target)
        self.update_target()

    def update_target(self):
        text = self.url_input.text().strip()
        kind, target_id = parse_target(text)
        valid = bool(kind and target_id)
        self.submit_button.setEnabled(valid)
        self.max_count.setEnabled(kind == "podcast")
        if kind == "podcast":
            self.target_badge.setText(f"已识别播客 · {target_id[:10]}…")
            state = "success"
        elif kind == "episode":
            self.target_badge.setText(f"已识别单期 · {target_id[:10]}…")
            state = "success"
        else:
            self.target_badge.setText("支持播客和单期链接" if not text else "未识别，请检查链接")
            state = "muted" if not text else "error"
        self.target_badge.setProperty("state", state)
        self.target_badge.style().unpolish(self.target_badge)
        self.target_badge.style().polish(self.target_badge)

    def submit(self):
        kind, target_id = parse_target(self.url_input.text())
        if not kind or not target_id:
            QMessageBox.warning(self, "无法识别", "请输入有效的小宇宙播客或节目链接。")
            return
        options = TaskOptions(
            fetch_transcripts=self.transcripts_check.isChecked(),
            comments_mode=self.comments_combo.currentData(),
            episodes_max_count=self.max_count.value() if kind == "podcast" else 0,
        )
        item = self.tasks.add_task(kind, target_id, options)
        self.selected_task_id = item.id
        self.url_input.clear()
        self.refresh_tasks()
        self.show_task_log(item.id)

    def refresh_tasks(self):
        selected = self.selected_task_id
        self.task_tree.blockSignals(True)
        self.task_tree.clear()
        colors = {
            "已完成": QColor(SUCCESS),
            "失败": QColor(DANGER),
            "已取消": QColor(MUTED),
            "运行中": QColor("#9DB2FF"),
            "正在取消": QColor(WARNING),
            "等待中": QColor(MUTED),
        }
        selected_item = None
        selected_task = None
        for task in self.tasks.tasks:
            short_id = f"{task.target_id[:12]}…"
            item = QTreeWidgetItem([task.display_name, short_id, task.status])
            item.setData(0, Qt.ItemDataRole.UserRole, task.id)
            item.setForeground(2, QBrush(colors.get(task.status, QColor(MUTED))))
            item.setToolTip(0, f"创建于 {task.created_at:%Y-%m-%d %H:%M:%S} · 阶段 {task.stage}")
            item.setToolTip(1, task.target_id)
            self.task_tree.addTopLevelItem(item)
            if task.id == selected:
                selected_item = item
                selected_task = task
        if selected_item:
            self.task_tree.setCurrentItem(selected_item)
        self.task_tree.blockSignals(False)
        self.task_stack.setCurrentIndex(1 if self.tasks.tasks else 0)
        self.queue_title.setText(f"任务队列 · {len(self.tasks.tasks)}")
        self.cancel_button.setEnabled(
            bool(selected_task and selected_task.status in {"等待中", "运行中"})
        )
        self.clear_button.setEnabled(
            any(task.status in {"已完成", "失败", "已取消"} for task in self.tasks.tasks)
        )
        if not self.tasks.tasks:
            self.selected_task_id = None
            self.log_stack.setCurrentIndex(0)

    def select_task(self):
        items = self.task_tree.selectedItems()
        if items:
            task_id = items[0].data(0, Qt.ItemDataRole.UserRole)
            self.selected_task_id = task_id
            task = next((task for task in self.tasks.tasks if task.id == task_id), None)
            self.cancel_button.setEnabled(
                bool(task and task.status in {"等待中", "运行中"})
            )
            self.show_task_log(task_id)
        else:
            self.cancel_button.setEnabled(False)

    def show_task_log(self, task_id: str):
        task = next((task for task in self.tasks.tasks if task.id == task_id), None)
        self.log_stack.setCurrentIndex(1 if task else 0)
        self.log_view.setPlainText(task.log if task else "")
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def append_output(self, task_id: str, text: str):
        if task_id == self.selected_task_id:
            self.log_view.moveCursor(self.log_view.textCursor().MoveOperation.End)
            self.log_view.insertPlainText(text)
            self.log_view.verticalScrollBar().setValue(
                self.log_view.verticalScrollBar().maximum()
            )

    def cancel_selected(self):
        if self.selected_task_id:
            self.tasks.cancel_task(self.selected_task_id)

    def update_active(self, task_id: str):
        if not task_id:
            set_status_pill(self.active_pill, "队列空闲", "neutral")
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.progress.setVisible(False)
            return
        set_status_pill(self.active_pill, "抓取运行中", "success")
        self.progress.setVisible(True)
        task = next((task for task in self.tasks.tasks if task.id == task_id), None)
        if task:
            stage = " · 最新一期评论" if task.stage == 2 else ""
            self.active_pill.setToolTip(f"{task.display_name}{stage}")
            self.progress.setRange(0, 0)


class DataPage(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, repository: Repository):
        super().__init__()
        self.repository = repository
        self.podcasts: list[dict] = []
        self.episodes: list[dict] = []
        self.current_bundle: dict | None = None
        self._episode_request = 0
        self._detail_request = 0
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)
        header = QHBoxLayout()
        header.addLayout(page_header("数据校验", "核对已抓取节目、逐字稿和评论，并导出结果"), 1)
        self.refresh_button = QPushButton("刷新数据")
        self.refresh_button.clicked.connect(self.refresh)
        self.export_list_button = QPushButton("导出节目清单")
        self.export_list_button.clicked.connect(self.export_list)
        header.addWidget(self.export_list_button)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        podcast_panel, podcast_layout = card_layout()
        podcast_title = card_title("播客")
        podcast_layout.addWidget(podcast_title)
        self.podcast_list = QListWidget()
        self.podcast_list.setSpacing(4)
        self.podcast_list.setWordWrap(True)
        self.podcast_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.podcast_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.podcast_list.itemSelectionChanged.connect(self.podcast_selected)
        podcast_layout.addWidget(self.podcast_list)
        splitter.addWidget(podcast_panel)

        episode_panel, episode_layout = card_layout()
        episode_header = QHBoxLayout()
        episode_title = card_title("节目")
        episode_header.addWidget(episode_title)
        episode_header.addStretch(1)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("筛选标题或 eid")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filter_episodes)
        episode_header.addWidget(self.search_input)
        episode_layout.addLayout(episode_header)
        self.episode_table = QTableWidget(0, 5)
        self.episode_table.setHorizontalHeaderLabels(
            ["标题", "日期", "时长", "逐字稿", "评论"]
        )
        self.episode_table.horizontalHeaderItem(1).setToolTip("发布日期")
        self.episode_table.horizontalHeaderItem(4).setToolTip("已抓评论数")
        self.episode_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.episode_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.episode_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.episode_table.setAlternatingRowColors(True)
        self.episode_table.verticalHeader().setVisible(False)
        self.episode_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        header = self.episode_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.episode_table.setColumnWidth(3, 92)
        self.episode_table.setColumnWidth(4, 92)
        self.episode_table.itemSelectionChanged.connect(self.episode_selected)
        episode_layout.addWidget(self.episode_table)
        splitter.addWidget(episode_panel)

        detail_panel, detail_layout = card_layout()
        detail_header = QHBoxLayout()
        detail_title = card_title("内容检查")
        detail_header.addWidget(detail_title)
        detail_header.addStretch(1)
        self.export_episode_button = QPushButton("导出当前期")
        self.export_episode_button.setEnabled(False)
        self.export_episode_button.clicked.connect(self.export_current_episode)
        detail_header.addWidget(self.export_episode_button)
        detail_layout.addLayout(detail_header)
        self.episode_detail_title = QLabel("选择一期节目查看内容")
        self.episode_detail_title.setObjectName("DetailTitle")
        self.episode_detail_title.setWordWrap(True)
        self.episode_detail_meta = meta_label(
            "选择节目后，这里会显示标题摘要、eid 与评论统计"
        )
        detail_layout.addWidget(self.episode_detail_title)
        detail_layout.addWidget(self.episode_detail_meta)
        self.detail_tabs = QTabWidget()
        self.info_view = self._text_view()
        self.transcript_view = self._text_view()
        self.comments_view = self._text_view()
        self.detail_tabs.addTab(self.info_view, "节目信息")
        self.detail_tabs.addTab(self.transcript_view, "逐字稿")
        self.detail_tabs.addTab(self.comments_view, "评论")
        detail_layout.addWidget(self.detail_tabs)
        splitter.setSizes([220, 760])
        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.addWidget(splitter)
        vertical_splitter.addWidget(detail_panel)
        vertical_splitter.setSizes([430, 250])
        vertical_splitter.setCollapsible(1, False)
        root.addWidget(vertical_splitter, 1)

    @staticmethod
    def _text_view() -> QTextBrowser:
        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setReadOnly(True)
        return view

    def refresh(self):
        self.refresh_button.setEnabled(False)
        self.podcast_list.clear()
        self.podcast_list.addItem("正在读取数据库…")
        self._podcast_worker = run_async(
            self.repository.list_podcasts, self._podcasts_loaded, self._load_error
        )

    def _podcasts_loaded(self, podcasts: list[dict]):
        self.refresh_button.setEnabled(True)
        self.podcasts = podcasts
        self.podcast_list.clear()
        for podcast in podcasts:
            completeness = (
                f"{podcast['transcripts']}/{podcast['episodes']} 逐字稿"
            )
            item = QListWidgetItem(
                f"{podcast['title']}\n{podcast['episodes']} 期 · {completeness}"
            )
            item.setData(Qt.ItemDataRole.UserRole, podcast["pid"])
            item.setToolTip(podcast["pid"])
            self.podcast_list.addItem(item)
        if podcasts:
            self.podcast_list.setCurrentRow(0)
        else:
            self.episodes = []
            self.populate_episodes()
        self.status_message.emit(f"已加载 {len(podcasts)} 个播客")

    def _load_error(self, message: str):
        self.refresh_button.setEnabled(True)
        self.podcast_list.clear()
        self.podcast_list.addItem("读取失败")
        self.status_message.emit(f"数据库错误：{message}")

    def current_pid(self) -> str | None:
        items = self.podcast_list.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    def podcast_selected(self):
        pid = self.current_pid()
        if not pid:
            return
        self._episode_request += 1
        request_id = self._episode_request
        self.search_input.clear()
        self.episode_table.setRowCount(0)
        self.current_bundle = None
        self.export_episode_button.setEnabled(False)
        self._episode_worker = run_async(
            lambda: self.repository.list_episodes(pid),
            lambda episodes: self._episodes_loaded(request_id, episodes),
            self._load_error,
        )

    def _episodes_loaded(self, request_id: int, episodes: list[dict]):
        if request_id != self._episode_request:
            return
        self.episodes = episodes
        self.populate_episodes()

    def populate_episodes(self):
        self.episode_table.setSortingEnabled(False)
        self.episode_table.setRowCount(len(self.episodes))
        for row, episode in enumerate(self.episodes):
            title = QTableWidgetItem(episode.get("title") or episode["eid"])
            title.setData(Qt.ItemDataRole.UserRole, episode["eid"])
            title.setToolTip(episode["eid"])
            self.episode_table.setItem(row, 0, title)
            date_item = QTableWidgetItem((episode.get("pubDate") or "")[:10])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.episode_table.setItem(row, 1, date_item)
            duration_item = QTableWidgetItem(format_duration(episode.get("duration")))
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.episode_table.setItem(row, 2, duration_item)
            transcript = QTableWidgetItem("有" if episode.get("has_transcript") else "缺")
            transcript.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            transcript.setForeground(QBrush(QColor(SUCCESS if episode.get("has_transcript") else WARNING)))
            self.episode_table.setItem(row, 3, transcript)
            comments = QTableWidgetItem(str(episode.get("fetched_comments", 0)))
            comments.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.episode_table.setItem(row, 4, comments)
        self.episode_table.setSortingEnabled(True)
        self.episode_table.sortItems(1, Qt.SortOrder.DescendingOrder)
        self.filter_episodes()

    def filter_episodes(self):
        query = self.search_input.text().strip().lower()
        for row in range(self.episode_table.rowCount()):
            title_item = self.episode_table.item(row, 0)
            text = (title_item.text() + " " + title_item.data(Qt.ItemDataRole.UserRole)).lower()
            self.episode_table.setRowHidden(row, bool(query and query not in text))

    def selected_eid(self) -> str | None:
        row = self.episode_table.currentRow()
        item = self.episode_table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def episode_selected(self):
        eid = self.selected_eid()
        if not eid:
            return
        self._detail_request += 1
        request_id = self._detail_request
        self.export_episode_button.setEnabled(False)
        self.episode_detail_title.setText("正在读取节目…")
        self.episode_detail_meta.setText(eid)
        self.info_view.setPlainText("正在读取…")
        self.transcript_view.clear()
        self.comments_view.clear()
        self._detail_worker = run_async(
            lambda: self.repository.episode_bundle(eid),
            lambda bundle: self._bundle_loaded(request_id, bundle),
            self._load_error,
        )

    def _bundle_loaded(self, request_id: int, bundle: dict):
        if request_id != self._detail_request:
            return
        self.current_bundle = bundle
        episode = bundle["episode"]
        transcript = bundle.get("transcript")
        comments = bundle.get("comments") or []
        self.episode_detail_title.setText(episode.get("title") or episode["eid"])
        self.episode_detail_meta.setText(
            f"{episode['eid']} · 发布 {(episode.get('pubDate') or '-')[:10]} · "
            f"时长 {format_duration(episode.get('duration'))} · "
            f"评论 {len(comments)}/{episode.get('commentCount', 0)}"
        )
        info = [
            "基本信息",
            f"eid：{episode['eid']}",
            f"pid：{episode.get('pid', '-')}",
            f"发布：{episode.get('pubDate', '-')}",
            f"时长：{format_duration(episode.get('duration'))}",
            f"平台评论数：{episode.get('commentCount', 0)}",
            f"已抓评论数：{len(comments)}",
            "",
            "简介",
            episode.get("description") or "无",
        ]
        if episode.get("shownotes"):
            info.extend(["", "Shownotes", episode["shownotes"]])
        self.info_view.setPlainText("\n".join(info))
        if transcript:
            lines = []
            if transcript.get("vendorDeclaration"):
                lines.extend([transcript["vendorDeclaration"], ""])
            lines.extend(
                f"[{format_ms(segment.get('startMs'))}] {segment.get('text', '')}"
                for segment in transcript.get("segments") or []
            )
            self.transcript_view.setPlainText("\n".join(lines))
        else:
            self.transcript_view.setPlainText("该期没有已抓取的逐字稿。")
        comment_lines = []
        for comment in comments:
            comment_lines.append(comment.get("text") or "")
            comment_lines.append(
                f"  {comment.get('likeCount', 0)} 赞 · {comment.get('id', '-')}"
            )
            comment_lines.append("")
        self.comments_view.setPlainText(
            "\n".join(comment_lines) if comment_lines else "该期没有已抓取的评论。"
        )
        self.export_episode_button.setEnabled(True)

    def export_list(self):
        if not self.episodes:
            self.status_message.emit("当前没有可导出的节目清单")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出节目清单", str(PROJECT_ROOT / "data" / "episodes.csv"), "CSV (*.csv)"
        )
        if not path:
            return
        try:
            export_episode_csv(self.episodes, path)
            self.status_message.emit(f"节目清单已导出：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def export_current_episode(self):
        if not self.current_bundle:
            return
        episode = self.current_bundle["episode"]
        has_srt = bool(episode_srt(self.current_bundle))
        filters = "Markdown (*.md);;JSON (*.json)"
        if has_srt:
            filters += ";;SRT 字幕 (*.srt)"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出当前节目",
            str(PROJECT_ROOT / "data" / f"{episode['eid']}.md"),
            filters,
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        fmt = "srt" if suffix == ".srt" else "json" if suffix == ".json" else "md"
        try:
            export_episode(self.current_bundle, path, fmt)
            self.status_message.emit(f"节目已导出：{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))


class SettingsPage(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, repository: Repository):
        super().__init__()
        self.repository = repository
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)
        root.addLayout(page_header("设置", "查看当前运行环境与凭据状态；配置修改后重启 GUI 生效"))

        environment_card, environment_layout = card_layout()
        environment_layout.addWidget(card_title("运行环境"))
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Python", selectable_label(sys.executable))
        self.database_label = selectable_label(repository.database_label)
        self.database_pill = status_pill("未测试", "neutral")
        database_row = QWidget()
        database_layout = QHBoxLayout(database_row)
        database_layout.setContentsMargins(0, 0, 0, 0)
        database_layout.setSpacing(10)
        database_layout.addWidget(self.database_label, 1)
        database_layout.addWidget(self.database_pill)
        form.addRow("MongoDB", database_row)
        form.addRow("配置文件", selectable_label(str(DEFAULT_CONFIG)))
        form.addRow("抓取入口", selectable_label(str(PROJECT_ROOT / "src" / "main.py")))
        environment_layout.addLayout(form)
        root.addWidget(environment_card)

        token_card, token_layout = card_layout()
        token_layout.addWidget(card_title("凭据与数据"))
        token_layout.addWidget(meta_label("Token 文件"))
        self.token_path = selectable_label("-")
        token_layout.addWidget(self.token_path)
        token_status_row = QHBoxLayout()
        token_status_row.setSpacing(10)
        self.access_pill = status_pill("access_token 未读取", "neutral")
        self.refresh_pill = status_pill("refresh_token 未读取", "neutral")
        self.token_updated = meta_label("最近更新：-")
        token_status_row.addWidget(self.access_pill)
        token_status_row.addWidget(self.refresh_pill)
        token_status_row.addStretch(1)
        token_status_row.addWidget(self.token_updated)
        token_layout.addLayout(token_status_row)
        button_row = QHBoxLayout()
        self.test_button = QPushButton("测试数据库连接")
        self.test_button.setObjectName("PrimaryButton")
        self.test_button.clicked.connect(self.test_connection)
        open_config = QPushButton("打开配置文件")
        open_config.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(DEFAULT_CONFIG)))
        )
        open_data = QPushButton("打开数据目录")
        open_data.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(DEFAULT_CONFIG.parent))
            )
        )
        button_row.addWidget(self.test_button)
        button_row.addWidget(open_config)
        button_row.addWidget(open_data)
        button_row.addStretch(1)
        token_layout.addLayout(button_row)
        root.addWidget(token_card)

        note = QLabel(
            "说明：GUI 复用原命令行抓取器，任务会独立运行并自动刷新 token。\n"
            "重复执行全量抓取会按原工具设计写入新的 task 记录；数据校验页按 eid 显示最新记录。"
        )
        note.setObjectName("Note")
        note.setWordWrap(True)
        root.addWidget(note)
        root.addStretch(1)
        self.load_token_status()

    def load_token_status(self):
        try:
            status = self.repository.token_status()
            self.token_path.setText(status["path"])
            set_status_pill(
                self.access_pill,
                "access_token 已配置" if status["access_token"] else "access_token 缺失",
                "success" if status["access_token"] else "error",
            )
            set_status_pill(
                self.refresh_pill,
                "refresh_token 已配置" if status["refresh_token"] else "refresh_token 缺失",
                "success" if status["refresh_token"] else "error",
            )
            self.token_updated.setText(f"最近更新：{status['modified']}")
        except Exception as exc:
            self.token_path.setText("无法读取 token 文件")
            set_status_pill(self.access_pill, "token 读取失败", "error")
            set_status_pill(self.refresh_pill, "token 读取失败", "error")
            self.token_updated.setText(str(exc))

    def test_connection(self):
        self.test_button.setEnabled(False)
        set_status_pill(self.database_pill, "正在测试", "warning")
        self._test_worker = run_async(
            self.repository.test_connection, self._connection_ok, self._connection_error
        )

    def _connection_ok(self, version: str):
        self.test_button.setEnabled(True)
        set_status_pill(self.database_pill, f"正常 · MongoDB {version}", "success")
        self.database_pill.setToolTip(f"MongoDB {version}")
        self.status_message.emit("数据库连接正常")

    def _connection_error(self, message: str):
        self.test_button.setEnabled(True)
        set_status_pill(self.database_pill, "连接失败", "error")
        self.database_pill.setToolTip(message)
        self.status_message.emit(f"数据库连接失败：{message}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.repository = Repository()
        self.tasks = TaskManager(self.repository)
        self.setWindowTitle("XYZ Fetcher · 小宇宙抓取工具")
        self.resize(1360, 860)
        self.setMinimumSize(1080, 700)

        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(190)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 22, 14, 16)
        side.setSpacing(8)
        brand = QLabel("XYZ Fetcher")
        brand.setObjectName("AppTitle")
        subtitle = QLabel("小宇宙抓取工具")
        subtitle.setObjectName("AppSubtitle")
        side.addWidget(brand)
        side.addWidget(subtitle)
        side.addSpacing(20)
        side.addWidget(meta_label("工作区"))
        side.addSpacing(6)

        self.stack = QStackedWidget()
        self.fetch_page = FetchPage(self.tasks)
        self.data_page = DataPage(self.repository)
        self.settings_page = SettingsPage(self.repository)
        for page in (self.fetch_page, self.data_page, self.settings_page):
            self.stack.addWidget(page)

        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        nav_items = (
            ("抓取任务", "tasks"),
            ("数据校验", "data"),
            ("设置", "settings"),
        )
        for index, (text, icon_name) in enumerate(nav_items):
            button = QPushButton(text)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setIcon(nav_icon(icon_name))
            button.setIconSize(QSize(17, 17))
            button.clicked.connect(lambda _=False, i=index: self.navigate(i))
            nav_group.addButton(button, index)
            side.addWidget(button)
            if index == 0:
                button.setChecked(True)
        side.addStretch(1)
        self.db_status = status_pill("数据库未测试", "neutral")
        self.db_status.setToolTip(self.repository.database_label)
        side.addWidget(self.db_status)
        version = QLabel("PyQt6 Desktop · v0.2")
        version.setObjectName("Meta")
        side.addWidget(version)
        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.task_status = meta_label("任务队列空闲")
        status.addWidget(self.task_status, 1)
        status.addPermanentWidget(meta_label(self.repository.database_label))
        self.tasks.active_changed.connect(self._active_status)
        self.tasks.task_finished.connect(self._task_finished)
        self.data_page.status_message.connect(self.statusBar().showMessage)
        self.settings_page.status_message.connect(self.statusBar().showMessage)
        self.data_page.refresh()
        self._test_worker = run_async(
            self.repository.test_connection, self._db_ok, self._db_error
        )

    def navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 2:
            self.settings_page.load_token_status()

    def _db_ok(self, version: str):
        set_status_pill(self.db_status, "数据库连接正常", "success")
        self.db_status.setToolTip(f"MongoDB {version} · {self.repository.database_label}")

    def _db_error(self, message: str):
        set_status_pill(self.db_status, "数据库连接失败", "error")
        self.statusBar().showMessage(f"数据库连接失败：{message}", 10000)

    def _active_status(self, task_id: str):
        self.task_status.setText("后台抓取运行中" if task_id else "任务队列空闲")

    def _task_finished(self, _task_id: str, success: bool):
        self.statusBar().showMessage("抓取任务完成" if success else "抓取任务未成功完成", 8000)
        self.data_page.refresh()
        self.settings_page.load_token_status()

    def closeEvent(self, event: QCloseEvent):
        if self.tasks.process is not None:
            answer = QMessageBox.question(
                self,
                "任务仍在运行",
                "退出将终止当前抓取子进程，确定退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.tasks.shutdown()
        self.repository.close()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("XYZ Fetcher")
    app.setOrganizationName("xyz-fetcher")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
