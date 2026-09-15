"""Tests for order service logic."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from src.orders.order_service import OrderService, OrderError


def test_create_order_empty_items():
    svc = OrderService()
    db = MagicMock()
    with pytest.raises(OrderError, match="at least one item"):
        svc.create_order(db, "user-1", [])


def test_cancel_order_invalid_status():
    svc = OrderService()
    db = MagicMock()
    order = MagicMock()
    order.status = "DELIVERED"
    order.user_id = "user-1"
    from src.orders.order_repository import OrderRepository
    with patch.object(OrderRepository, "find_by_id", return_value=order):
        with pytest.raises(OrderError, match="cannot be cancelled"):
            svc.cancel_order(db, "order-1", "user-1")


def test_valid_transitions():
    svc = OrderService()
    assert "CANCELLED" in svc.VALID_TRANSITIONS["PENDING"]
    assert "CONFIRMED" in svc.VALID_TRANSITIONS["PENDING"]
    assert "SHIPPED" in svc.VALID_TRANSITIONS["CONFIRMED"]
    assert len(svc.VALID_TRANSITIONS["DELIVERED"]) == 0


def test_invalid_advance_transition():
    svc = OrderService()
    db = MagicMock()
    order = MagicMock()
    order.status = "PENDING"
    from src.orders.order_repository import OrderRepository
    with patch.object(OrderRepository, "find_by_id", return_value=order):
        with pytest.raises(OrderError, match="Cannot transition"):
            svc.advance_status(db, "order-1", "DELIVERED")


def test_access_denied_wrong_user():
    svc = OrderService()
    db = MagicMock()
    order = MagicMock()
    order.user_id = "user-correct"
    from src.orders.order_repository import OrderRepository
    with patch.object(OrderRepository, "find_by_id", return_value=order):
        with pytest.raises(OrderError, match="Access denied"):
            svc.get_order(db, "order-1", "user-wrong")
