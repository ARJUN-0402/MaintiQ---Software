"""EDA / Visualisation page: distributions and target balance for the active dataset."""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.widgets.canvas import MatplotlibCanvas


class EDAPage(BasePage):
    """Exploratory visualisations for the active dataset."""

    NUMERIC_COLUMNS = (
        "air_temperature_k",
        "process_temperature_k",
        "rotational_speed_rpm",
        "torque_nm",
        "tool_wear_min",
    )

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("EDA / Visualisation")
        self.set_subtitle(
            "Distributions of numeric attributes and target balance for the active dataset."
        )

        controls = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh charts")
        self.btn_refresh.setObjectName("primary")
        controls.addWidget(self.btn_refresh)
        controls.addStretch()
        self._content_layout.addLayout(controls)

        self._canvas = MatplotlibCanvas(width=10, height=6)
        self._content_layout.addWidget(self._canvas, 1)

        self._note = QLabel(
            "Charts are computed from the imported dataset only. They describe the data, "
            "not model performance, and are not certified industrial analysis."
        )
        self._note.setWordWrap(True)
        self._note.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        self._content_layout.addWidget(self._note)

        self._content_layout.addStretch()

        self.btn_refresh.clicked.connect(self._draw)

    def on_shown(self) -> None:
        self._draw()

    def _draw(self) -> None:
        try:
            frame = self.service.active_frame
        except Exception as exc:
            self.show_error(f"Could not read dataset: {exc}")
            return
        if frame is None or len(frame) == 0:
            self.show_empty("Import a dataset to view EDA charts.")
            self._canvas.clear()
            return

        self.hide_empty()
        self.clear_banner()
        figure = self._canvas.figure
        figure.clear()

        axes = figure.subplots(2, 3)
        axes = axes.ravel()

        for index, column in enumerate(self.NUMERIC_COLUMNS):
            ax = axes[index]
            if column in frame.columns:
                values = frame[column].to_numpy(dtype=float, na_value=np.nan)
                values = values[np.isfinite(values)]
                if values.size:
                    ax.hist(values, bins=20, color="#0ea5e9", edgecolor="#0369a1")
                    ax.set_title(column.replace("_", " ").title())
                    ax.set_xlabel("")
                    ax.set_ylabel("Count")
                    ax.grid(alpha=0.3)
                else:
                    ax.set_title(f"{column} (no valid values)")
                    ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
            else:
                ax.set_title(f"{column} (missing)")
                ax.axis("off")

        ax = axes[5]
        target_column = "machine_failure"
        if target_column in frame.columns:
            counts = frame[target_column].value_counts().sort_index()
            ax.bar([str(i) for i in counts.index], counts.values, color=["#2dd4bf", "#fb923c"])
            ax.set_title("Target balance")
            ax.set_xlabel("Machine failure (0 = no, 1 = yes)")
            ax.set_ylabel("Rows")
            ax.grid(axis="y", alpha=0.3)
        else:
            ax.set_title("Target column not present")
            ax.axis("off")

        figure.tight_layout()
        self._canvas.canvas.draw_idle()
