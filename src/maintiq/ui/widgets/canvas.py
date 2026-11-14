"""Matplotlib canvas widget embedded in Qt pages.

Uses the QtAgg backend so figures render inside the native desktop window
without a browser or web engine. Figure creation here is purely decorative:
all chart data and drawing logic live in :mod:`maintiq.ml.evaluation.charts`.

The canvas applies the application's dark theme to every figure so charts
never flash a white background against the dark UI. Axes created on the figure
inherit a dark panel facecolor and readable light text/tick colours.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg", force=True)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

# Dark theme colours mirroring src/maintiq/ui/styles.py.
_FIGURE_FACE = "#0f172a"
_AXES_FACE = "#111827"
_TEXT_COLOR = "#e8eaf2"
_TICK_COLOR = "#94a3b8"
_GRID_COLOR = "#334155"
_SPINE_COLOR = "#475569"


def _apply_dark_theme(figure: Figure) -> None:
    """Style a figure and its existing axes for the dark application theme."""
    figure.patch.set_facecolor(_FIGURE_FACE)
    for ax in figure.axes:
        ax.set_facecolor(_AXES_FACE)
        ax.tick_params(colors=_TICK_COLOR, which="both")
        ax.xaxis.label.set_color(_TEXT_COLOR)
        ax.yaxis.label.set_color(_TEXT_COLOR)
        ax.title.set_color(_TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color(_SPINE_COLOR)
        if ax.get_legend() is not None:
            ax.get_legend().get_frame().set_facecolor(_AXES_FACE)
            ax.get_legend().get_frame().set_edgecolor(_SPINE_COLOR)
            for text in ax.get_legend().get_texts():
                text.set_color(_TEXT_COLOR)


class MatplotlibCanvas(QWidget):
    """A QWidget wrapping a matplotlib FigureCanvas with a resize policy."""

    def __init__(
        self, parent: QWidget | None = None, width: float = 6.0, height: float = 4.0, dpi: int = 100
    ) -> None:
        super().__init__(parent)
        self._figure = Figure(figsize=(width, height), dpi=dpi, facecolor=_FIGURE_FACE)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._canvas.updateGeometry()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.setLayout(layout)

        _apply_dark_theme(self._figure)

    @property
    def figure(self) -> Figure:
        return self._figure

    @property
    def canvas(self) -> FigureCanvas:
        return self._canvas

    def clear(self) -> None:
        self._figure.clear()
        _apply_dark_theme(self._figure)
        self._canvas.draw_idle()
