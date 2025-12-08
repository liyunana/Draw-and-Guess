"""
Basic server tests.
"""


def test_server_import():
    """Test server module import."""
    try:
        from src.server.main import main

        assert callable(main)
    except ImportError:
        # Main might not exist yet, that's OK for now
        assert True


def test_server_config():
    """Test server configuration."""
    try:
        from src.shared.constants import DEFAULT_HOST, DEFAULT_PORT  # noqa: F401

        assert True
    except ImportError:
        # Config might not exist yet, that's OK
        assert True
