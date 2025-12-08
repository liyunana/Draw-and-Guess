"""
Basic tests to ensure pytest is working correctly.
"""

def test_always_pass():
    """A test that always passes to verify pytest setup."""
    assert True

def test_import_project():
    """Test that project modules can be imported."""
    try:
        import src
        import src.server
        import src.client
        import src.shared
        assert True
    except ImportError as e:
        assert False, f"Failed to import project modules: {e}"

def test_version():
    """Test that version info is available."""
    from src import __version__
    assert __version__ == "0.1.0"
    assert isinstance(__version__, str)