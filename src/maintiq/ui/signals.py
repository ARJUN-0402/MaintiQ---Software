"""Qt signals and result dataclasses for background workers.

Workers run long-running operations (training, prediction, explanation,
report export) off the GUI thread and communicate results/errors through
typed Qt signals so widgets never block the event loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QObject, Signal


@dataclass
class TaskResult:
    """Outcome of a background task run on the worker pool."""

    task_id: str
    ok: bool
    result: Any = None
    error: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


class WorkerSignals(QObject):
    """Signals emitted by a :class:`~maintiq.ui.worker.Task` running on a worker thread."""

    started = Signal(str)
    progress = Signal(str)
    result = Signal(object)
    error = Signal(str)
    finished = Signal(str)
