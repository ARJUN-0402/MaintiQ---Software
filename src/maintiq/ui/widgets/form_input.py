"""Prediction input form: the six canonical AI4I attributes with validation hints."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)

from maintiq.data.schema import CANONICAL_PREDICTIVE_INPUTS, TYPE_VALUES, UNITS

# Numeric spin bounds (physically meaningful domains, not clamps).
_NUMERIC_BOUNDS = {
    "air_temperature_k": (200.0, 400.0),
    "process_temperature_k": (200.0, 500.0),
    "rotational_speed_rpm": (0.0, 5000.0),
    "torque_nm": (0.0, 100.0),
    "tool_wear_min": (0.0, 300.0),
}


class PredictionInputForm(QWidget):
    """Input controls for the six supported predictive attributes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controls: dict[str, QComboBox | QDoubleSpinBox] = {}

        group = QGroupBox("Machine attributes")
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        type_combo = QComboBox()
        type_combo.addItems(list(TYPE_VALUES))
        self._controls["type"] = type_combo
        form.addRow("Machine type", type_combo)

        for column in CANONICAL_PREDICTIVE_INPUTS:
            if column == "type":
                continue
            minimum, maximum = _NUMERIC_BOUNDS[column]
            spin = QDoubleSpinBox()
            spin.setRange(minimum, maximum)
            spin.setDecimals(2)
            spin.setValue(0.0)
            spin.setSuffix(f" {UNITS[column]}")
            self._controls[column] = spin
            form.addRow(f"{column.replace('_', ' ').title()}", spin)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)
        layout.addStretch()

    def values(self) -> dict[str, str | float]:
        """Return the current input values keyed by canonical column name."""
        result: dict[str, str | float] = {}
        for column, control in self._controls.items():
            if isinstance(control, QComboBox):
                result[column] = control.currentText()
            else:
                result[column] = float(control.value())
        return result

    def set_values(self, values: dict[str, str | float]) -> None:
        """Populate controls from a dict keyed by canonical column name."""
        for column, value in values.items():
            control = self._controls.get(column)
            if control is None:
                continue
            if isinstance(control, QComboBox):
                index = control.findText(str(value))
                if index >= 0:
                    control.setCurrentIndex(index)
            else:
                control.setValue(float(value))

    def clear(self) -> None:
        self._controls["type"].setCurrentIndex(0)
        for column, control in self._controls.items():
            if column == "type":
                continue
            control.setValue(0.0)
