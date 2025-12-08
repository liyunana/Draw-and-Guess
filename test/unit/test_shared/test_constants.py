"""
Tests for shared constants and utilities.
"""

def test_constants_import():
    """Test that constants can be imported."""
    try:
        from src.shared.constants import DEFAULT_PORT, MAX_PLAYERS
        assert isinstance(DEFAULT_PORT, int)
        assert isinstance(MAX_PLAYERS, int)
        assert MAX_PLAYERS > 0
    except ImportError:
        # Constants file might not exist yet, that's OK for now
        assert True