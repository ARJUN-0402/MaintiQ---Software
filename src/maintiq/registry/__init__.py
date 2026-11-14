"""Local model registry package.

Re-exports the concrete :class:`~maintiq.ml.training.registry.ModelRegistry`
implementation so consumers can import from ``maintiq.registry`` as well as
``maintiq.ml.training``.
"""

from maintiq.ml.training.registry import ModelRegistry

__all__ = ["ModelRegistry"]
