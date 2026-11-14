"""Matplotlib canvas widget embedded in Qt pages.

Uses the QtAgg backend so figures render inside the native desktop window
without a browser or web engine. Figure creation here is purely decorative:
all chart data and drawing logic live in :mod:`maintiq.ml.evaluation.charts`.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg", force=True)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget


class MatplotlibCanvas(QWidget):
    """A QWidget wrapping a matplotlib FigureCanvas with a resize policy."""

    def __init__(
        self, parent: QWidget | None = None, width: float = 6.0, height: float = 4.0, dpi: int = 100
    ) -> None:
        super().__init__(parent)
        self._figure = Figure(figsize=(width, height), dpi=dpi)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._canvas.updateGeometry()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.setLayout(layout)

    @property
    def figure(self) -> Figure:
        return self._figure

    @property
    def canvas(self) -> FigureCanvas:
        return self._canvas

    def clear(self) -> None:
        self._figure.clear()
        self._canvas.draw_idle()
