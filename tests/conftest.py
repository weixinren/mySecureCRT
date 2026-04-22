import pytest
from PyQt5.QtWidgets import QApplication
import sys


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests requiring Qt."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit the app, as it may be needed by other tests


@pytest.fixture(autouse=True)
def ensure_qapp(qapp):
    """Automatically ensure QApplication exists for all tests."""
    pass
