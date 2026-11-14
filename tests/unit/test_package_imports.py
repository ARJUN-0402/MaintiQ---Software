"""Tests for package import and metadata."""

from importlib import metadata

import maintiq


def test_package_imports():
    """The maintiq package imports and exposes title/version/description."""
    assert maintiq.__title__ == "MaintiQ"
    assert maintiq.__version__
    assert "academic" in maintiq.__description__.lower()


def test_package_version_is_registered():
    """The package version is discoverable via importlib.metadata."""
    dist = metadata.version("maintiq")
    assert dist == maintiq.__version__
