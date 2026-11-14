"""Background task runner built on QRunnable and QThreadPool.

Long-running ML work (training, prediction with explanation, report export)
runs off the GUI thread. Results and errors are delivered to the GUI thread
through :class:`WorkerSignals` so widgets never freeze and never touch Qt
objects from a worker thread directly.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
import uuid

from PySide6.QtCore import QRunnable, QThreadPool, Slot

from maintiq.ui.signals import TaskResult, WorkerSignals


class Task(QRunnable):
    """A single background task executed on the application thread pool."""

    def __init__(
        self,
        task_id: str | None,
        fn: Callable[[], Any],
        signals: WorkerSignals,
    ) -> None:
        super().__init__()
        self.task_id = task_id or str(uuid.uuid4())
        self._fn = fn
        self._signals = signals
        self.setAutoDelete(True)

    @Slot()  # runs on a worker thread
    def run(self) -> None:
        self._signals.started.emit(self.task_id)
        try:
            result = self._fn()
        except Exception as exc:  # worker boundary: capture, never propagate to thread
            self._signals.error.emit(f"{self.task_id}: {type(exc).__name__}: {exc}")
        else:
            self._signals.result.emit(TaskResult(task_id=self.task_id, ok=True, result=result))
        finally:
            self._signals.finished.emit(self.task_id)


class TaskRunner:
    """Submits :class:`Task` instances to the shared application thread pool."""

    def __init__(self, pool: QThreadPool | None = None) -> None:
        self._pool = pool or QThreadPool.globalInstance()
        self._signals_by_task: dict[str, WorkerSignals] = {}

    def submit(
        self,
        fn: Callable[[], Any],
        *,
        task_id: str | None = None,
        on_started: Callable[[str], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
        on_result: Callable[[TaskResult], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_finished: Callable[[str], None] | None = None,
    ) -> str:
        """Run ``fn`` on a worker thread and deliver the outcome through callbacks.

        Callbacks are invoked on the GUI thread via queued signal delivery.
        Returns the task id.
        """
        task_id = task_id or str(uuid.uuid4())
        signals = WorkerSignals()
        if on_started is not None:
            signals.started.connect(on_started)
        if on_progress is not None:
            signals.progress.connect(on_progress)
        if on_result is not None:
            signals.result.connect(on_result)
        if on_error is not None:
            signals.error.connect(on_error)
        if on_finished is not None:
            signals.finished.connect(on_finished)
        # Keep the signal object alive until its queued deliveries are done;
        # the task auto-deletes itself on completion, which would otherwise
        # drop in-flight cross-thread signal events.
        signals.finished.connect(lambda tid=task_id: self._signals_by_task.pop(tid, None))
        self._signals_by_task[task_id] = signals

        task = Task(task_id=task_id, fn=fn, signals=signals)
        self._pool.start(task)
        return task.task_id

    def wait_for_all(self, msecs: int = -1) -> bool:
        """Block until all submitted tasks finish (useful in tests)."""
        return self._pool.waitForDone(msecs)
