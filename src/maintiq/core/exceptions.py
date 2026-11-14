"""Custom exception types for expected application errors.

All MaintiQ-specific exceptions inherit from ``MaintiQError`` so callers can
catch application failures distinctly from unexpected interpreter errors.
"""

from __future__ import annotations


class MaintiQError(Exception):
    """Base exception for all MaintiQ application errors."""


class ConfigurationError(MaintiQError):
    """Raised when application configuration is invalid or incomplete."""


class PathError(MaintiQError):
    """Raised when a required path cannot be resolved or created."""


class DatasetError(MaintiQError):
    """Raised for dataset loading, validation, or import problems."""


class ValidationError(MaintiQError):
    """Raised when user input or data fails validation."""


class PreprocessingError(MaintiQError):
    """Raised when preprocessing cannot be fitted or applied."""


class FeatureEngineeringError(MaintiQError):
    """Raised when feature engineering cannot be applied."""


class ModelError(MaintiQError):
    """Raised for model training, loading, or inference failures."""


class ModelNotFoundError(ModelError):
    """Raised when a requested model version is not registered."""


class ModelHashMismatchError(ModelError):
    """Raised when a model artefact's SHA-256 does not match the registry."""


class ModelLoadRejectedError(ModelError):
    """Raised when a model file is rejected as untrusted or corrupted."""


class RegistryError(MaintiQError):
    """Raised for model registry read/write or corruption problems."""


class ExplanationError(MaintiQError):
    """Raised when an explanation cannot be produced."""


class PredictionError(MaintiQError):
    """Raised when a single-record prediction cannot be completed."""


class ReportError(MaintiQError):
    """Raised when report generation or export fails."""


class SettingsError(MaintiQError):
    """Raised when application settings are invalid or cannot be persisted."""
