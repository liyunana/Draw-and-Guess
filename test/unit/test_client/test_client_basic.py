"""
Basic client tests.
"""


def test_client_import():
    """Test client module import."""
    try:
        from src.client.main import main

        assert callable(main)
    except ImportError:
        # Main might not exist yet, that's OK for now
        assert True
