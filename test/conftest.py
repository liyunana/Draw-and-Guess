"""
Pytest configuration and shared fixtures for Draw and Guess game.
"""

import os
import sys

import pytest

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def sample_player_data():
    """Sample player data for testing."""
    return {"name": "TestPlayer", "score": 0, "id": 1, "is_drawer": False}


@pytest.fixture
def sample_room_data():
    """Sample room data for testing."""
    return {"room_id": "test_room_123", "players": [], "max_players": 8, "game_state": "waiting"}
