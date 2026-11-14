"""Main window: navigation shell hosting all application pages.

The window is a thin presentation layer: it wires navigation to stacked pages
and delegates all data, training, prediction and reporting work to the
injected :class:`~maintiq.services.ApplicationService`.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from maintiq import __academic_notice__, __title__, __version__
from maintiq.config import get_config
from maintiq.services import ApplicationService
from maintiq.ui.pages import (
    AboutPage,
    DashboardPage,
    DatasetExplorerPage,
    EDAPage,
    ExplainPage,
    ModelPerformancePage,
    ModelRegistryPage,
    ModelTrainingPage,
    PredictPage,
    ReportsPage,
    SettingsPage,
    ThresholdPage,
)

# Navigation entries in display order: (page key, label, page class)
NAVIGATION: list[tuple[str, str, type[QWidget]]] = [
    ("dashboard", "Dashboard", DashboardPage),
    ("predict", "Predict Failure", PredictPage),
    ("explain", "Explain Prediction", ExplainPage),
    ("dataset", "Dataset Explorer", DatasetExplorerPage),
    ("eda", "EDA / Visualisation", EDAPage),
    ("performance", "Model Performance", ModelPerformancePage),
    ("threshold", "Threshold Analysis", ThresholdPage),
    ("training", "Model Training", ModelTrainingPage),
    ("registry", "Model Registry", ModelRegistryPage),
    ("reports", "Reports and Downloads", ReportsPage),
    ("settings", "Settings", SettingsPage),
    ("about", "About / Limitations", AboutPage),
]


class MainWindow(QMainWindow):
    """Shell window with sidebar navigation and a stacked set of page widgets."""

    def __init__(self, service: ApplicationService) -> None:
        super().__init__()
        self._service = service
        self.setWindowTitle(f"{__title__} v{__version__}")
        self.setMinimumSize(1100, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top band: navigation sidebar + stacked pages.
        band = QWidget()
        band_layout = QHBoxLayout(band)
        band_layout.setContentsMargins(0, 0, 0, 0)
        band_layout.setSpacing(0)

        self._navigation = QListWidget()
        self._navigation.setObjectName("navigation")
        self._navigation.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        for _key, label, _cls in NAVIGATION:
            item = QListWidgetItem(label)
            item.setSizeHint(QSize(0, 40))
            self._navigation.addItem(item)
        self._navigation.currentRowChanged.connect(self._switch_page)

        self._pages = QStackedWidget()
        self._page_widgets: dict[str, QWidget] = {}
        for key, _label, page_cls in NAVIGATION:
            page = page_cls(service=service)
            page.setObjectName(key)
            self._page_widgets[key] = page
            self._pages.addWidget(page)

        band_layout.addWidget(self._navigation, 0)
        band_layout.addWidget(self._pages, 1)
        root.addWidget(band, 1)

        # Persistent academic-prototype notice at the bottom.
        self._notice = QFrame()
        self._notice.setObjectName("notice")
        notice_layout = QVBoxLayout(self._notice)
        notice_layout.setContentsMargins(12, 8, 12, 8)
        notice_layout.setSpacing(4)
        title = QLabel("Academic prototype notice")
        title.setStyleSheet("font-weight: 700; font-size: 13px; color: #fde68a;")
        body = QLabel(__academic_notice__)
        body.setObjectName("noticeText")
        body.setWordWrap(True)
        notice_layout.addWidget(title)
        notice_layout.addWidget(body)
        root.addWidget(self._notice)

        self._setup_menu_bar()
        self._setup_status_bar()

        self._navigation.setCurrentRow(0)

    # ------------------------------------------------------------------ setup

    def _setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        import_action = QAction("&Import dataset...", self)
        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self._import_dataset)
        file_menu.addAction(import_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About / Limitations", self)
        about_action.triggered.connect(lambda: self._navigate_to("about"))
        help_menu.addAction(about_action)

    def _setup_status_bar(self) -> None:
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------ navigation

    def _switch_page(self, row: int) -> None:
        if row < 0 or row >= len(NAVIGATION):
            return
        key, _label, _cls = NAVIGATION[row]
        page = self._page_widgets[key]
        self._pages.setCurrentWidget(page)
        on_shown = getattr(page, "on_shown", None)
        if callable(on_shown):
            try:
                on_shown()
            except Exception:  # navigation must never crash the shell
                pass
        self.statusBar().showMessage(f"{__title__} — {key}")

    def _navigate_to(self, key: str) -> None:
        for index, (nav_key, _label, _cls) in enumerate(NAVIGATION):
            if nav_key == key:
                self._navigation.setCurrentRow(index)
                return

    # ------------------------------------------------------------------ actions

    @Slot()
    def _import_dataset(self) -> None:
        start_dir = str(get_config().paths.user_datasets_dir)
        path, _ = self._file_dialog_open(start_dir)
        if path:
            page = self._page_widgets.get("dataset")
            if page is not None and hasattr(page, "import_path"):
                page.import_path(path)
            self._navigate_to("dataset")

    def _file_dialog_open(self, start_dir: str) -> tuple[str, str]:
        return QFileDialog.getOpenFileName(
            self,
            "Import dataset CSV",
            start_dir,
            "CSV files (*.csv);;All files (*)",
        )
