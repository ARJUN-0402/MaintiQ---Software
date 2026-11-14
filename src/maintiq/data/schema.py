"""Dataset schema for the AI4I 2020 Predictive Maintenance Dataset.

Defines canonical field names, source-to-canonical column mapping, expected
types, categorical values, the target definition, excluded columns, and unit
descriptions. All internal code uses the canonical names below.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Canonical predictive input names used internally by MaintiQ.
CANONICAL_PREDICTIVE_INPUTS = (
    "type",
    "air_temperature_k",
    "process_temperature_k",
    "rotational_speed_rpm",
    "torque_nm",
    "tool_wear_min",
)

# Canonical target name.
CANONICAL_TARGET = "machine_failure"

# All columns the model may consume (predictive inputs only).
CANONICAL_FEATURE_COLUMNS = CANONICAL_PREDICTIVE_INPUTS

# Columns that must never be used as predictive inputs.
EXCLUDED_COLUMNS = (
    "udi",
    "product_id",
    "twf",
    "hdf",
    "pwf",
    "osf",
    "rnf",
)

# Expected categorical values for ``type``.
TYPE_VALUES = ("L", "M", "H")

# Numeric domains considered physically impossible / invalid.
NUMERIC_DOMAINS = {
    "air_temperature_k": (0.0, None),  # must be positive
    "process_temperature_k": (0.0, None),  # must be positive
    "rotational_speed_rpm": (0.0, None),  # must be strictly positive
    "torque_nm": (0.0, None),  # must be non-negative
    "tool_wear_min": (0.0, None),  # must be non-negative
}

# Units for documentation and axis labels.
UNITS = {
    "type": "category (L/M/H)",
    "air_temperature_k": "Kelvin (K)",
    "process_temperature_k": "Kelvin (K)",
    "rotational_speed_rpm": "revolutions per minute (rpm)",
    "torque_nm": "Newton-metres (Nm)",
    "tool_wear_min": "minutes (min)",
    "machine_failure": "binary (0 = no failure, 1 = failure)",
}


@dataclass(frozen=True)
class ColumnMapping:
    """Maps a source dataset column to a canonical internal name."""

    source: str
    canonical: str


@dataclass(frozen=True)
class DatasetSchema:
    """Complete schema contract for an AI4I-style predictive maintenance CSV."""

    target_column: str = CANONICAL_TARGET
    predictive_inputs: tuple[str, ...] = CANONICAL_PREDICTIVE_INPUTS
    feature_columns: tuple[str, ...] = CANONICAL_FEATURE_COLUMNS
    excluded_columns: tuple[str, ...] = EXCLUDED_COLUMNS
    type_values: tuple[str, ...] = TYPE_VALUES
    numeric_domains: dict[str, tuple[float, float | None]] = field(
        default_factory=lambda: dict(NUMERIC_DOMAINS)
    )
    units: dict[str, str] = field(default_factory=lambda: dict(UNITS))

    # Default AI4I 2020 source header -> canonical name mapping.
    source_to_canonical: tuple[ColumnMapping, ...] = field(
        default_factory=lambda: (
            ColumnMapping("Type", "type"),
            ColumnMapping("Air temperature [K]", "air_temperature_k"),
            ColumnMapping("Process temperature [K]", "process_temperature_k"),
            ColumnMapping("Rotational speed [rpm]", "rotational_speed_rpm"),
            ColumnMapping("Torque [Nm]", "torque_nm"),
            ColumnMapping("Tool wear [min]", "tool_wear_min"),
            ColumnMapping("Machine failure", "machine_failure"),
            ColumnMapping("UDI", "udi"),
            ColumnMapping("Product ID", "product_id"),
            ColumnMapping("TWF", "twf"),
            ColumnMapping("HDF", "hdf"),
            ColumnMapping("PWF", "pwf"),
            ColumnMapping("OSF", "osf"),
            ColumnMapping("RNF", "rnf"),
        )
    )

    def canonical_for(self, source_column: str) -> str | None:
        """Return the canonical name for a source column, or None if unmapped."""
        for mapping in self.source_to_canonical:
            if mapping.source == source_column:
                return mapping.canonical
        return None

    def source_for(self, canonical: str) -> str | None:
        """Return the source name for a canonical column, or None."""
        for mapping in self.source_to_canonical:
            if mapping.canonical == canonical:
                return mapping.source
        return None

    def required_source_columns(self) -> tuple[str, ...]:
        """Source columns required for a valid predictive dataset."""
        return tuple(
            mapping.source
            for mapping in self.source_to_canonical
            if mapping.canonical in self.feature_columns or mapping.canonical == self.target_column
        )

    def is_excluded(self, column: str) -> bool:
        """Return True if a column must never be a predictive input."""
        return column in self.excluded_columns
