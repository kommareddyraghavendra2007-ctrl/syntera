"""
OrderRepository — data access layer for Order and OrderItem entities.

Called by OrderService.
"""
from __future__ import annotations
from decimal import Decimal
from sqlalchemy.orm import Session
from src.database.models import Order, OrderItem, Product


class OrderRepository:
    """Data access for Order and OrderItem tables."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, order_id: str) -> Order | None:
        return self._db.query(Order).filter(Order.id == order_id).first()

    def find_by_user(self, user_id: str, limit: int = 50) -> list[Order]:
        return (
            self._db.query(Order)
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .all()
        )

    def create(self, user_id: str, items: list[dict], shipping_address: str | None) -> Order:
        """
        Create an order with line items.

        items: list of {"product_id": str, "quantity": int, "unit_price": Decimal}
        """
        total = sum(
            item["unit_price"] * item["quantity"]
            for item in items
        )
        order = Order(
            user_id=user_id,
            status="PENDING",
            total_amount=total,
            shipping_address=shipping_address,
        )
        self._db.add(order)
        self._db.flush()  # get order.id
        for item in items:
            subtotal = item["unit_price"] * item["quantity"]
            self._db.add(OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                subtotal=subtotal,
            ))
        self._db.commit()
        self._db.refresh(order)
        return order

    def update_status(self, order: Order, status: str) -> Order:
        order.status = status
        self._db.commit()
        self._db.refresh(order)
        return order
