import time
import pytest
from fastapi import Request
from unittest.mock import MagicMock, patch

from src.utils.lazy_proxy import LazyProxy
from src.utils.api_utils import retry_api_call
from src.utils.validation import validate_safe_param
from src.utils.rate_limiter import RateLimiter
from src.utils.task_tracker import TaskTracker
from src.utils.idempotency import clean_expired_keys, _memory_cache
from src.utils.redis_client import cache_get, cache_set, cache_delete, cache_ping


class TestLazyProxy:
    def test_lazy_instantiation(self):
        """LazyProxy should not instantiate the factory until first access."""
        called = False
        def factory():
            nonlocal called
            called = True
            return {"key": "value"}
        proxy = LazyProxy(factory)
        assert called is False
        assert proxy["key"] == "value"
        assert called is True

    def test_getattr(self):
        proxy = LazyProxy(lambda: {"a": 1})
        assert proxy["a"] == 1

    def test_call(self):
        proxy = LazyProxy(lambda: lambda x: x * 2)
        assert proxy(5) == 10

    def test_repr_and_str(self):
        proxy = LazyProxy(lambda: "hello")
        assert repr(proxy) == repr("hello")
        assert str(proxy) == str("hello")

    def test_len_and_contains(self):
        proxy = LazyProxy(lambda: [1, 2, 3])
        assert len(proxy) == 3
        assert 2 in proxy

    def test_iter(self):
        proxy = LazyProxy(lambda: [10, 20])
        assert list(proxy) == [10, 20]

    def test_setattr(self):
        class Obj:
            pass
        proxy = LazyProxy(lambda: Obj())
        proxy.x = 42
        assert proxy.x == 42

    def test_context_manager(self):
        class Ctx:
            def __enter__(self):
                return "entered"
            def __exit__(self, *args):
                pass
        proxy = LazyProxy(lambda: Ctx())
        with proxy as p:
            assert p == "entered"


class TestRetryApiCall:
    def test_retry_success_first_try(self):
        func = MagicMock(return_value="ok")
        assert retry_api_call(func, retries=3) == "ok"
        func.assert_called_once()

    def test_retry_success_after_failures(self):
        func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])
        assert retry_api_call(func, retries=3) == "ok"
        assert func.call_count == 3

    def test_retry_exhausted_raises(self):
        func = MagicMock(side_effect=ValueError("persistent"))
        with pytest.raises(ValueError, match="persistent"):
            retry_api_call(func, retries=2)
        assert func.call_count == 3


class TestValidation:
    def test_valid_params(self):
        validate_safe_param("alice")
        validate_safe_param("Bob_02")
        validate_safe_param("hello-world")
        validate_safe_param("test.file")
        validate_safe_param("contact name")
        assert True

    def test_invalid_params(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            validate_safe_param("contact<script>")
        assert exc.value.status_code == 400

    def test_special_chars_rejected(self):
        from fastapi import HTTPException
        for bad in ["hello^world", "test!name", "at@sign", "dollar$",
                     "percent%", "caret^", "question?", "slash/test",
                     "back\\slash", "colon:test", "asterisk*", "quote'test"]:
            with pytest.raises(HTTPException):
                validate_safe_param(bad)

    def test_empty_string(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_safe_param("")

    def test_too_long(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_safe_param("a" * 101)


class TestRateLimiter:
    def test_under_limit(self):
        limiter = RateLimiter(requests_limit=5, window_seconds=60)
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "10.0.0.1"
        for _ in range(5):
            limiter(mock_request)

    def test_over_limit(self):
        limiter = RateLimiter(requests_limit=3, window_seconds=60)
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "10.0.0.2"
        for _ in range(3):
            limiter(mock_request)
        with pytest.raises(Exception) as exc:
            limiter(mock_request)
        assert "Rate limit exceeded" in str(exc.value)

    def test_sliding_window_expiry(self):
        limiter = RateLimiter(requests_limit=2, window_seconds=1)
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "10.0.0.3"
        limiter(mock_request)
        limiter(mock_request)
        time.sleep(1.1)
        # Window should have rolled
        limiter(mock_request)

    def test_different_ips_separate_counters(self):
        limiter = RateLimiter(requests_limit=1, window_seconds=60)
        r1 = MagicMock(spec=Request)
        r1.client.host = "10.0.0.4"
        r2 = MagicMock(spec=Request)
        r2.client.host = "10.0.0.5"
        limiter(r1)
        limiter(r2)  # different IP, should pass


class TestTaskTracker:
    def test_register_and_complete(self):
        tracker = TaskTracker()
        tracker.register_task("t1", "Test Task", total=10)
        tasks = tracker.get_active_tasks()
        assert any(t["id"] == "t1" and t["status"] == "running" for t in tasks)
        tracker.complete_task("t1")
        tasks = tracker.get_active_tasks()
        assert any(t["id"] == "t1" and t["status"] == "completed" for t in tasks)

    def test_update_progress(self):
        tracker = TaskTracker()
        tracker.register_task("t2", "Progress Task", total=100)
        tracker.update_task("t2", 50)
        tasks = tracker.get_active_tasks()
        t = next(t for t in tasks if t["id"] == "t2")
        assert t["current"] == 50

    def test_fail_task(self):
        tracker = TaskTracker()
        tracker.register_task("t3", "Fail Task")
        tracker.fail_task("t3", "Something went wrong")
        tasks = tracker.get_active_tasks()
        t = next(t for t in tasks if t["id"] == "t3")
        assert t["status"] == "failed"
        assert t["error"] == "Something went wrong"

    def test_cancel_request(self):
        tracker = TaskTracker()
        tracker.register_task("t4", "Cancel Task")
        assert tracker.is_cancelled("t4") is False
        tracker.request_cancel("t4")
        assert tracker.is_cancelled("t4") is True
        tasks = tracker.get_active_tasks()
        t = next(t for t in tasks if t["id"] == "t4")
        assert t["status"] == "cancelling"

    def test_cancel_nonexistent(self):
        tracker = TaskTracker()
        assert tracker.is_cancelled("nonexistent") is False
        tracker.request_cancel("nonexistent")


class TestIdempotency:
    def setup_method(self):
        _memory_cache.clear()

    def test_clean_mixed_keys(self):
        _memory_cache["old"] = (time.time() - 10, 200, {})
        _memory_cache["new"] = (time.time() + 1000, 200, {})
        clean_expired_keys()
        assert "old" not in _memory_cache
        assert "new" in _memory_cache


class TestRedisClient:
    @patch("src.utils.redis_client.REDIS_ENABLED", True)
    @patch("src.utils.redis_client._get_client")
    def test_cache_get_returns_none_when_unavailable(self, mock_get_client):
        mock_get_client.return_value = None
        assert cache_get("test_key") is None

    @patch("src.utils.redis_client.REDIS_ENABLED", True)
    @patch("src.utils.redis_client._get_client")
    def test_cache_set_returns_false_when_unavailable(self, mock_get_client):
        mock_get_client.return_value = None
        assert cache_set("test_key", "value") is False

    @patch("src.utils.redis_client.REDIS_ENABLED", True)
    @patch("src.utils.redis_client._get_client")
    def test_cache_delete_returns_false_when_unavailable(self, mock_get_client):
        mock_get_client.return_value = None
        assert cache_delete("test_key") is False

    @patch("src.utils.redis_client.REDIS_ENABLED", True)
    @patch("src.utils.redis_client._get_client")
    def test_cache_ping_returns_false_when_unavailable(self, mock_get_client):
        mock_get_client.return_value = None
        assert cache_ping() is False
