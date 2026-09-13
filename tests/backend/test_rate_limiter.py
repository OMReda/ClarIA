import pytest
from unittest.mock import MagicMock, patch
from backend.services.rate_limiter import check_and_increment, get_current_count

@pytest.fixture
def mock_redis():
    with patch("backend.services.rate_limiter._get_redis") as mock_get_redis:
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        yield mock_client

def test_check_and_increment_allowed(mock_redis):
    # Simulate first request (Lua script returns 1)
    mock_redis.eval.return_value = 1
    allowed, count = check_and_increment("user-123")
    
    assert allowed is True
    assert count == 1
    mock_redis.eval.assert_called_once()

def test_check_and_increment_rate_limited(mock_redis):
    # Simulate exceeding the limit (e.g., 31)
    with patch("backend.services.rate_limiter.settings.rate_limit_prompts_per_hour", 30):
        mock_redis.eval.return_value = 31
        allowed, count = check_and_increment("user-456")
        
        assert allowed is False
        assert count == 31

def test_check_and_increment_redis_unavailable():
    # If redis raises an exception, the rate limiter should fail open
    with patch("backend.services.rate_limiter._get_redis", side_effect=Exception("Connection Error")):
        allowed, count = check_and_increment("user-789")
        assert allowed is True
        assert count == 0

def test_get_current_count(mock_redis):
    mock_redis.get.return_value = "5"
    count = get_current_count("user-123")
    assert count == 5
    mock_redis.get.assert_called_once()

def test_get_current_count_empty(mock_redis):
    mock_redis.get.return_value = None
    count = get_current_count("user-123")
    assert count == 0

def test_get_current_count_redis_unavailable():
    with patch("backend.services.rate_limiter._get_redis", side_effect=Exception("Connection Error")):
        count = get_current_count("user-123")
        assert count == 0
