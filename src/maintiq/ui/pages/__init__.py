"""Public page classes exposed by the :mod:`maintiq.ui.pages` package."""

from maintiq.ui.pages.about import AboutPage
from maintiq.ui.pages.base import BasePage
from maintiq.ui.pages.dashboard import DashboardPage
from maintiq.ui.pages.dataset import DatasetExplorerPage
from maintiq.ui.pages.eda import EDAPage
from maintiq.ui.pages.explain import ExplainPage
from maintiq.ui.pages.model_performance import ModelPerformancePage
from maintiq.ui.pages.model_registry import ModelRegistryPage
from maintiq.ui.pages.model_training import ModelTrainingPage
from maintiq.ui.pages.predict import PredictPage
from maintiq.ui.pages.reports import ReportsPage
from maintiq.ui.pages.settings import SettingsPage
from maintiq.ui.pages.threshold import ThresholdPage

__all__ = [
    "AboutPage",
    "BasePage",
    "DashboardPage",
    "DatasetExplorerPage",
    "EDAPage",
    "ExplainPage",
    "ModelPerformancePage",
    "ModelRegistryPage",
    "ModelTrainingPage",
    "PredictPage",
    "ReportsPage",
    "SettingsPage",
    "ThresholdPage",
]
