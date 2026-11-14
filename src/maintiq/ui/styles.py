"""Application stylesheet.

Restrained industrial palette: navy and charcoal surfaces, neutral borders,
one teal accent for primary actions, clear success/warning/error states.
Designed to scale with standard Windows DPI settings.
"""

APP_STYLESHEET = """
QWidget {
    font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: #e8eaf2;
    background-color: #0f172a;
}
QMainWindow {
    background-color: #0f172a;
}
QStatusBar {
    background-color: #0b1021;
    color: #94a3b8;
    border-top: 1px solid #1e293b;
    padding: 4px 8px;
}
QMenuBar {
    background-color: #0b1021;
    color: #cbd5e1;
    border-bottom: 1px solid #1e293b;
    padding: 2px 4px;
}
QMenuBar::item:selected {
    background-color: #14203d;
    color: #7dd3fc;
}
QMenu {
    background-color: #0b1021;
    color: #cbd5e1;
    border: 1px solid #1e293b;
}
QMenu::item:selected {
    background-color: #14203d;
    color: #7dd3fc;
}
QToolTip {
    background-color: #1e293b;
    color: #e8eaf2;
    border: 1px solid #334155;
    padding: 4px 8px;
}

/* Sidebar navigation */
#navigation {
    background-color: #0b1021;
    border-right: 1px solid #1e293b;
    min-width: 210px;
    max-width: 210px;
}
QListWidget#navigation {
    outline: none;
    background-color: #0b1021;
}
QListWidget::item {
    color: #94a3b8;
    padding: 10px 14px;
    border-bottom: 1px solid #121930;
    text-align: left;
}
QListWidget::item:selected {
    background-color: #14203d;
    color: #7dd3fc;
    border-left: 3px solid #2dd4bf;
}
QListWidget::item:hover:!selected {
    background-color: #121930;
    color: #cbd5e1;
}

/* Page container */
QStackedWidget {
    background-color: #0f172a;
}

/* Headings */
QLabel#pageTitle {
    font-size: 22px;
    font-weight: 600;
    color: #ffffff;
    padding: 0;
}
QLabel#pageSubtitle {
    font-size: 13px;
    color: #94a3b8;
}

/* Cards */
QFrame#card {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 14px;
    color: #e8eaf2;
}
QFrame#card:hover {
    border-color: #334155;
}
QLabel#cardValue {
    font-size: 20px;
    font-weight: 700;
    color: #7dd3fc;
}
QLabel#cardLabel {
    font-size: 12px;
    color: #94a3b8;
}

/* Buttons */
QPushButton {
    background-color: #14203d;
    color: #e8eaf2;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    min-width: 90px;
}
QPushButton:hover {
    background-color: #1e293b;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #0f172a;
}
QPushButton:disabled {
    background-color: #0f172a;
    color: #475569;
    border-color: #1e293b;
}
QPushButton#primary {
    background-color: #0ea5e9;
    color: #002233;
    border: none;
    font-weight: 600;
}
QPushButton#primary:hover {
    background-color: #38bdf8;
}
QPushButton#accent {
    background-color: #2dd4bf;
    color: #002233;
    border: none;
    font-weight: 600;
}
QPushButton#accent:hover {
    background-color: #5eead4;
}
QPushButton#danger {
    background-color: #7f1d1d;
    color: #fee2e2;
    border: 1px solid #991b1b;
}
QPushButton#danger:hover {
    background-color: #991b1b;
}

/* Status banner */
QFrame#statusBanner {
    border-radius: 6px;
    padding: 10px 14px;
}
QFrame#statusBanner#info {
    background-color: #164e63;
    border: 1px solid #2dd4bf;
    color: #bae6fd;
}
QFrame#statusBanner#warning {
    background-color: #7c2d12;
    border: 1px solid #fb923c;
    color: #fdba74;
}
QFrame#statusBanner#error {
    background-color: #7f1d1d;
    border: 1px solid #fca5a5;
    color: #fecaca;
}
QFrame#statusBanner#success {
    background-color: #14532d;
    border: 1px solid #4ade80;
    color: #bbf7d0;
}
QLabel#statusBannerText {
    color: inherit;
    font-size: 12px;
}

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0b1021;
    color: #e8eaf2;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 28px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #0ea5e9;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QAbstractItemView {
    background-color: #0b1021;
    color: #e8eaf2;
    selection-background-color: #14203d;
    border: 1px solid #334155;
}

/* Tables */
QTableView, QTableWidget {
    background-color: #0b1021;
    color: #e8eaf2;
    gridline-color: #1e293b;
    border: 1px solid #1e293b;
    border-radius: 6px;
    selection-background-color: #14203d;
    selection-color: #7dd3fc;
}
QHeaderView::section {
    background-color: #111827;
    color: #94a3b8;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #1e293b;
    border-bottom: 1px solid #1e293b;
    font-weight: 600;
}
QTableCornerButton::section {
    background-color: #111827;
    border: none;
}

/* Progress bar */
QProgressBar {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 6px;
    text-align: center;
    color: #e8eaf2;
    min-height: 18px;
}
QProgressBar::chunk {
    background-color: #2dd4bf;
    border-radius: 5px;
}

/* Academic notice */
QFrame#notice {
    background-color: #1e1b16;
    border: 1px solid #451a03;
    border-radius: 6px;
    padding: 10px 14px;
    color: #fef3c7;
}
QLabel#noticeText {
    color: #fef3c7;
    font-size: 12px;
}
"""
