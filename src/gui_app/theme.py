# SPDX-License-Identifier: MIT
"""Visual theme for the desktop tool."""

from pathlib import Path

ACCENT = "#6D8DFF"
SUCCESS = "#45B98A"
WARNING = "#D7A84A"
DANGER = "#E06C75"
MUTED = "#8B98A9"

STYLE = """
* {
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 15px;
    color: #DCE3EC;
}
QMainWindow, QDialog { background: #0E141B; }
QWidget#Central { background: #0E141B; }
QFrame#Sidebar {
    background: #101822;
    border-right: 1px solid #1F2934;
}
QLabel#AppTitle { font-size: 21px; font-weight: 700; color: #F5F8FC; }
QLabel#AppSubtitle, QLabel[muted="true"] { color: #7E8DA0; }
QLabel#PageTitle { font-size: 27px; font-weight: 650; color: #F5F8FC; }
QLabel#SectionTitle { font-size: 16px; font-weight: 600; color: #EDF2F8; }
QLabel#CardTitle { font-size: 16px; font-weight: 650; color: #F0F4FA; }
QLabel#DetailTitle { font-size: 18px; font-weight: 650; color: #F3F6FA; }
QLabel#Meta, QLabel#EmptySubtitle { font-size: 13px; color: #7B899D; }
QLabel#TargetBadge {
    color: #8C9AAF;
    padding: 4px 0;
}
QLabel#TargetBadge[state="success"] { color: #70CBA4; }
QLabel#TargetBadge[state="error"] { color: #E99198; }
QLabel#EmptyTitle { font-size: 17px; font-weight: 600; color: #B4C0CE; }
QLabel#Note {
    background: #131D27;
    border-left: 3px solid #425B91;
    border-radius: 8px;
    padding: 12px 14px;
    color: #8D9BAD;
}
QLabel#StatusPill {
    border-radius: 11px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: 600;
    background: #22303F;
    border: 1px solid #2E3D4D;
    color: #AEBBCB;
}
QLabel#StatusPill[state="success"] {
    background: #17352B;
    border-color: #245C45;
    color: #71CFA5;
}
QLabel#StatusPill[state="warning"] {
    background: #3A2F16;
    border-color: #5C4A1E;
    color: #E0B45F;
}
QLabel#StatusPill[state="error"] {
    background: #3A1F24;
    border-color: #5E2F36;
    color: #EA9AA1;
}
QFrame#Card {
    background: #17212B;
    border: 1px solid #22303D;
    border-radius: 14px;
}
QPushButton {
    background: #202B37;
    border: 1px solid #2D3A48;
    border-radius: 8px;
    padding: 9px 15px;
    min-height: 21px;
}
QPushButton:hover { background: #283644; border-color: #3A4A5B; }
QPushButton:pressed { background: #1A242F; }
QPushButton:disabled { color: #647184; background: #18212B; border-color: #232E39; }
QPushButton#PrimaryButton {
    background: #6D8DFF;
    border: 1px solid #7C99FF;
    color: #0B1322;
    font-weight: 650;
}
QPushButton#PrimaryButton:hover { background: #809CFF; }
QPushButton#PrimaryButton:pressed { background: #5F7FEA; }
QPushButton#DangerButton { color: #F1A4AB; border-color: #58343A; background: #2C2026; }
QPushButton#NavButton {
    background: transparent;
    border: none;
    border-radius: 9px;
    color: #93A2B4;
    text-align: left;
    padding: 11px 14px;
    font-size: 15px;
    font-weight: 550;
}
QPushButton#NavButton:hover { background: #1A2530; color: #DCE3EC; }
QPushButton#NavButton:checked {
    background: #22304A;
    color: #C6D2FF;
    border-left: 3px solid #6D8DFF;
    padding-left: 11px;
    font-weight: 650;
}
QLineEdit, QComboBox, QSpinBox {
    background: #101820;
    border: 1px solid #2B3947;
    border-radius: 8px;
    padding: 9px 11px;
    selection-background-color: #415B9E;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #6D8DFF; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { color: #657387; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #18222D;
    border: 1px solid #344353;
    selection-background-color: #2C3E60;
    padding: 4px;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #405064;
    border-radius: 4px;
    background: #101820;
}
QCheckBox::indicator:checked { background: #6D8DFF; border-color: #6D8DFF; }
QListWidget, QTreeWidget, QTableWidget, QPlainTextEdit, QTextBrowser {
    background: #111922;
    border: 1px solid #24303D;
    border-radius: 8px;
    alternate-background-color: #141D27;
    outline: none;
}
QListWidget::item, QTreeWidget::item { padding: 8px; }
QListWidget::item:selected, QTreeWidget::item:selected {
    background: #22304A;
    color: #DCE5FF;
}
QListWidget::item:hover, QTreeWidget::item:hover { background: #1B2733; }
QTableWidget { gridline-color: #222D38; font-size: 13.5px; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #1D2731; }
QTableWidget::item:selected { background: #22304A; color: #E5EBFF; }
QHeaderView::section {
    background: #18222C;
    color: #96A4B5;
    border: none;
    border-bottom: 1px solid #2A3643;
    padding: 9px 7px;
    font-weight: 600;
}
QPlainTextEdit#LogView {
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    color: #B7C4D3;
    padding: 8px;
}
QTabWidget::pane { border: 1px solid #24303D; border-radius: 8px; background: #111922; }
QTabBar::tab {
    background: transparent;
    color: #8E9CAE;
    padding: 9px 14px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: #B9C8FF; border-bottom-color: #6D8DFF; }
QProgressBar {
    background: #101820;
    border: 1px solid #263340;
    border-radius: 5px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk { background: #6D8DFF; border-radius: 4px; }
QStatusBar { background: #101822; border-top: 1px solid #1F2934; color: #8493A5; padding: 4px 10px; }
QStatusBar::item { border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #354353; min-height: 30px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #46586C; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #354353; min-width: 30px; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip { background: #25313E; color: #E7EDF4; border: 1px solid #3B4A5B; padding: 5px; }
QSplitter::handle { background: #0E141B; width: 5px; }
"""

_CHECK_ICON = (Path(__file__).resolve().parent / "assets" / "check.svg").as_posix()
STYLE += f"""
QCheckBox::indicator:checked {{
    image: url("{_CHECK_ICON}");
}}
"""
