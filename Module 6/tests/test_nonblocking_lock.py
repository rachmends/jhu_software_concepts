"""Tests for the legacy nonblocking lock helper."""

import threading

import pytest

from app import NonBlockingLock


def test_lock_acquired_and_released():
    """An available lock is acquired and released."""
    lock = threading.Lock()

    with NonBlockingLock(lock) as acquired:
        assert acquired is True
        assert lock.locked() is True

    assert lock.locked() is False


def test_lock_already_held():
    """An unavailable lock is not acquired or released."""
    lock = threading.Lock()
    lock.acquire()

    try:
        with NonBlockingLock(lock) as acquired:
            assert acquired is False
            assert lock.locked() is True

        assert lock.locked() is True
    finally:
        lock.release()


def test_lock_released_after_exception():
    """The lock is released even when an exception occurs."""
    lock = threading.Lock()

    with pytest.raises(RuntimeError, match="Test failure"):
        with NonBlockingLock(lock) as acquired:
            assert acquired is True
            raise RuntimeError("Test failure")

    assert lock.locked() is False
