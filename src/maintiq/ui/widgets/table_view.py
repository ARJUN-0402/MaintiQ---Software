"""Generic read-only table view for displaying structured rows."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)


class TableView(QTableWidget):
    """A read-only table built from a list of dict rows and an ordered column list."""

    def __init__(self, columns: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns = list(columns)
        self.setColumnCount(len(self._columns))
        self.setHorizontalHeaderLabels(self._columns)
        self.setRowCount(0)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().hide()

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        """Replace the table contents with ``rows`` (dicts keyed by column)."""
        self.setRowCount(0)
        self.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, column in enumerate(self._columns):
                value = row.get(column, "")
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
                self.setItem(row_index, col_index, item)

    def clear(self) -> None:
        self.setRowCount(0)
