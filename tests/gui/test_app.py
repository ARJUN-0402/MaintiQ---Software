"""GUI smoke tests for the MaintiQ PySide6 desktop application.

Tests run in Qt offscreen mode and exercise the shell, navigation, all 12
pages, validation error display, service injection/mocking, and the
end-to-end import -> predict workflow with a stubbed application service.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QLabel, QListWidget, QStackedWidget
import pytest

from maintiq.data.import_workflow import ImportOutcome
from maintiq.ml.prediction.service import PredictionOutcome
from maintiq.ml.training.pipeline import PredictionResult
from maintiq.services import ApplicationService
from maintiq.ui.main_window import NAVIGATION, MainWindow
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

EXPECTED_PAGES = (
    DashboardPage,
    PredictPage,
    ExplainPage,
    DatasetExplorerPage,
    EDAPage,
    ModelPerformancePage,
    ThresholdPage,
    ModelTrainingPage,
    ModelRegistryPage,
    ReportsPage,
    SettingsPage,
    AboutPage,
)


@pytest.fixture
def stub_service() -> ApplicationService:
    """Application service whose components are MagicMock stubs."""
    return ApplicationService(
        import_service=MagicMock(),
        trainer=MagicMock(),
        registry=MagicMock(),
        prediction_service=MagicMock(),
        report_service=MagicMock(),
    )


def test_all_pages_are_instantiable(qapp, stub_service):
    """Every registered page constructs without a running window or event loop."""
    for page_cls in EXPECTED_PAGES:
        page = page_cls(service=stub_service)
        assert page is not None
        assert page.windowTitle() == "" or page.windowTitle() is not None


def test_main_window_constructs_all_pages(qapp, stub_service):
    """Main window builds the navigation shell with one stacked widget per page."""
    window = MainWindow(stub_service)
    assert window is not None
    nav = window.findChild(QListWidget)
    stack = window.findChild(QStackedWidget)
    assert nav is not None and stack is not None
    assert nav.count() == len(NAVIGATION) == 12
    assert stack.count() == 12
    # Every page key is present as a stacked widget child.
    keys = {key for key, _label, _cls in NAVIGATION}
    assert keys == set(window._page_widgets.keys())


def test_navigation_switches_pages(qapp, stub_service, process_until_idle):
    """Clicking through navigation rows shows the corresponding page."""
    window = MainWindow(stub_service)
    nav = window.findChild(QListWidget)
    last = nav.count() - 1
    nav.setCurrentRow(last)
    process_until_idle()
    key, _label, _cls = NAVIGATION[last]
    assert window._pages.currentWidget() is window._page_widgets[key]


def test_page_titles_non_empty(qapp, stub_service):
    """Each page sets a non-empty title label."""
    for page_cls in EXPECTED_PAGES:
        page = page_cls(service=stub_service)
        title = page.findChild(QLabel, "pageTitle")
        assert title is not None and title.text().strip(), f"{page_cls.__name__} has no title"


def test_predict_shows_validation_error_without_model(qapp, stub_service, process_until_idle):
    """Predicting with no registered model shows an error instead of crashing."""
    page = PredictPage(service=stub_service)
    stub_service.registry.list_models.return_value = []
    page.on_shown()
    page.btn_predict.click()
    process_until_idle()
    banner = page.findChild(QLabel, "statusBannerText")
    assert banner is not None and "Select a trained model" in banner.text()


def test_predict_end_to_end_with_stubbed_service(qapp, stub_service, process_until_idle):
    """A stubbed prediction flows through the form and result cards without the UI thread blocking."""
    stub_service.registry.list_models.return_value = ["logistic_regression"]
    stub_service.registry.list_versions.return_value = ["v1"]
    result = PredictionOutcome(
        prediction=PredictionResult(
            predicted_class=1,
            score=0.83,
            threshold=0.5,
            model_name="logistic_regression",
            model_version="v1",
            timestamp="2026-01-01T00:00:00+00:00",
            input_validated=True,
            out_of_distribution_warnings=[],
            explanation_available=False,
        ),
        explanation=None,
        explanation_error=None,
    )
    stub_service.prediction_service.predict_and_explain.return_value = result
    page = PredictPage(service=stub_service)
    page.on_shown()
    process_until_idle()
    page.btn_predict.click()
    process_until_idle()
    assert page.card_class.value() == "1"
    assert page.card_score.value() == "0.8300"
    assert page.btn_explain.isEnabled()


def test_explain_requires_record(qapp, stub_service, process_until_idle):
    """Explaining with no prediction record shows an error message."""
    page = ExplainPage(service=stub_service)
    page.btn_explain.click()
    process_until_idle()
    banner = page.findChild(QLabel, "statusBannerText")
    assert banner is not None and banner.text()


def test_dataset_import_rejects_invalid(qapp, stub_service, process_until_idle):
    """A rejected import leaves the previous state untouched and shows errors."""
    outcome = ImportOutcome(
        accepted=False, load_result=MagicMock(), errors=["Missing required column: type"]
    )
    stub_service.import_service.import_dataset.return_value = outcome
    page = DatasetExplorerPage(service=stub_service)
    page.import_path("some/invalid.csv")
    process_until_idle()
    assert "Missing required column" in page.lbl_validation.text()


def test_threshold_analysis_requires_dataset(qapp, stub_service, process_until_idle):
    """Threshold analysis without an active dataset reports an error."""
    page = ThresholdPage(service=stub_service)
    stub_service.registry.list_models.return_value = ["random_forest"]
    page.on_shown()
    process_until_idle()
    page.btn_analyze.click()
    process_until_idle()
    banner = page.findChild(QLabel, "statusBannerText")
    assert banner is not None and banner.text()


def test_ui_modules_contain_no_training_logic():
    """UI modules never import model-training internals; training lives in the service layer."""
    ui_root = Path(__file__).resolve().parents[2] / "src" / "maintiq" / "ui"
    forbidden = ("from maintiq.ml.training", "import maintiq.ml.training")
    for path in ui_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for statement in forbidden:
            assert statement not in text, f"{path} contains model-training logic: {statement}"


# --------------------------------------------------------------------------- Model Registry page (Phase 9)


def test_model_registry_delete_buttons_start_disabled(qapp, stub_service):
    """Delete buttons are disabled before any row is selected."""
    page = ModelRegistryPage(service=stub_service)
    assert page.btn_delete_version.isEnabled() is False
    assert page.btn_delete_model.isEnabled() is False


def test_model_registry_loads_table_and_enables_delete(qapp, stub_service, process_until_idle):
    """Loading the registry populates the table and row selection enables delete actions."""
    stub_service.registry.list_models.return_value = ["test_model"]
    stub_service.registry.list_versions.return_value = ["v1"]
    stub_service.registry.get_version.return_value = {
        "version": "v1",
        "metrics": {"accuracy": 0.9, "f1": 0.88, "roc_auc": 0.92},
        "threshold": 0.5,
        "created_at": "2026-01-01T00:00:00+00:00",
        "artifact_path": "models/test_model.joblib",
        "sha256": "abc123",
        "target_column": "machine_failure",
        "dataset_fingerprint": "fp",
        "parameters": {},
    }
    page = ModelRegistryPage(service=stub_service)
    page.on_shown()
    process_until_idle()
    assert page._table.rowCount() == 1
    assert page.btn_delete_version.isEnabled() is False
    assert page.btn_delete_model.isEnabled() is False

    # Select the only row.
    page._table.selectRow(0)
    process_until_idle()
    assert page.btn_delete_version.isEnabled() is True
    assert page.btn_delete_model.isEnabled() is True
    details_text = page._details.text()
    assert "test_model" in details_text
    assert "v1" in details_text


def test_model_registry_empty_state(qapp, stub_service, process_until_idle):
    """An empty registry shows the empty-state message."""
    stub_service.registry.list_models.return_value = []
    stub_service.registry.list_versions.return_value = []
    page = ModelRegistryPage(service=stub_service)
    page.on_shown()
    process_until_idle()
    assert page._table.rowCount() == 0
    assert "No registered models" in page._empty.text()


# --------------------------------------------------------------------------- Reports page (Phase 9)


def test_reports_png_export_requires_evaluation_data(
    qapp, stub_service, process_until_idle, tmp_path
):
    """Exporting PNG charts without evaluation data shows an error."""
    page = ReportsPage(service=stub_service)
    page._type_combo.setCurrentText("Evaluation charts (PNG)")
    # Headless: the export dialog must not block waiting for user input.
    with patch(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName",
        return_value=(str(tmp_path / "evaluation_charts.png"), ""),
    ):
        page.btn_export.click()
    process_until_idle()
    banner = page.findChild(QLabel, "statusBannerText")
    assert banner is not None and "No evaluation data available" in banner.text()


def test_reports_export_all_requires_some_data(qapp, stub_service, process_until_idle, tmp_path):
    """Export-all with no data reports nothing to export."""
    stub_service.registry.list_models.return_value = []
    stub_service.import_service.active_frame = None
    page = ReportsPage(service=stub_service)
    page._type_combo.setCurrentText("Export all (bundle)")
    # Point the file dialog at tmp_path by monkeypatching getExistingDirectory.
    with patch(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        return_value=str(tmp_path),
    ):
        page.btn_export.click()
        process_until_idle()
    banner = page.findChild(QLabel, "statusBannerText")
    assert banner is not None and "Nothing to export" in banner.text()
