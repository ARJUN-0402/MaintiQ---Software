from maintiq import __description__, __title__, __version__

__all__ = ["__description__", "__title__", "__version__"]


def main() -> int:
    """Application entry point: launch the native PySide6 desktop GUI."""
    from maintiq.ui.app import run  # noqa: PLC0415 - keep `import maintiq` light; GUI is optional at import time

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
