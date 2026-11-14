"""Tests for the dataset schema module."""

from maintiq.data.schema import DatasetSchema


def test_schema_defaults():
    """Schema exposes the canonical predictive inputs, target, and exclusions."""
    schema = DatasetSchema()
    assert schema.target_column == "machine_failure"
    assert "type" in schema.predictive_inputs
    assert "air_temperature_k" in schema.predictive_inputs
    assert "machine_failure" not in schema.predictive_inputs
    assert "udi" in schema.excluded_columns
    assert "product_id" in schema.excluded_columns
    assert "twf" in schema.excluded_columns
    assert "hdf" in schema.excluded_columns
    assert "pwf" in schema.excluded_columns
    assert "osf" in schema.excluded_columns
    assert "rnf" in schema.excluded_columns


def test_schema_column_mapping():
    """Source headers map to canonical names and back."""
    schema = DatasetSchema()
    assert schema.canonical_for("Type") == "type"
    assert schema.canonical_for("Machine failure") == "machine_failure"
    assert schema.source_for("type") == "Type"
    assert schema.canonical_for("Not A Column") is None


def test_schema_required_source_columns():
    """Required source columns include inputs and target, not exclusions."""
    schema = DatasetSchema()
    required = schema.required_source_columns()
    assert "Type" in required
    assert "Air temperature [K]" in required
    assert "Machine failure" in required
    assert "UDI" not in required
    assert "TWF" not in required


def test_schema_is_excluded():
    """Excluded columns are flagged; predictive inputs are not."""
    schema = DatasetSchema()
    assert schema.is_excluded("udi") is True
    assert schema.is_excluded("twf") is True
    assert schema.is_excluded("type") is False
    assert schema.is_excluded("machine_failure") is False
