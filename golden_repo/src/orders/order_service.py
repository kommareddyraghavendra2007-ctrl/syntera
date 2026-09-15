"""
OrderService — order lifecycle business logic.

Flow for order creation:
  1. Validate items exist and are in stock
  2. Create order record and line items via OrderRepository
  3. Reserve stock

Called by: api/orders.py
Calls: OrderRepository, database models
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.database.models import Order, Product
from src.orders.order_repository import OrderRepository


class OrderError(Exception):
    """Raised when an order operation fails."""


class OrderService:
    """Manages the complete order lifecycle."""

    VALID_TRANSITIONS: dict[str, set[str]] = {
        "PENDING": {"CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"SHIPPED", "CANCELLED"},
        "SHIPPED": {"DELIVERED"},
        "DELIVERED": set(),
        "CANCELLED": set(),
    }

    def create_order(
        self,
        db: Session,
        user_id: str,
        items: list[dict],
        shipping_address: str | None = None,
    ) -> Order:
        """
        Create a new order.

        items: list of {"product_id": str, "quantity": int}
        Raises OrderError on invalid product or insufficient stock.
        """
        if not items:
            raise OrderError("Order must contain at least one item")

        enriched = []
        for item in items:
            product = (
                db.query(Product)
                .filter(Product.id == item["product_id"], Product.is_active.is_(True))
                .first()
            )
            if not product:
                raise OrderError(f"Product {item['product_id']} not found or inactive")
            qty = int(item.get("quantity", 0))
            if qty <= 0:
                raise OrderError(f"Invalid quantity {qty} for product {product.sku}")
            if product.stock_quantity < qty:
                raise OrderError(
                    f"Insufficient stock for {product.sku}: "
                    f"requested {qty}, available {product.stock_quantity}"
                )
            enriched.append(
                {
                    "product_id": product.id,
                    "quantity": qty,
                    "unit_price": product.price,
                }
            )

        # Reserve stock
        for item_data in enriched:
            product = (
                db.query(Product).filter(Product.id == item_data["product_id"]).first()
            )
            if product:
                product.stock_quantity -= item_data["quantity"]

        repo = OrderRepository(db)
        return repo.create(
            user_id=user_id,
            items=enriched,
            shipping_address=shipping_address,
        )

    def get_order(self, db: Session, order_id: str, user_id: str) -> Order:
        """Get order by ID. Enforces user ownership."""
        repo = OrderRepository(db)
        order = repo.find_by_id(order_id)
        if not order:
            raise OrderError(f"Order {order_id} not found")
        if order.user_id != user_id:
            raise OrderError("Access denied to this order")
        return order

    def get_user_orders(self, db: Session, user_id: str) -> list[Order]:
        """Return all orders for a user."""
        repo = OrderRepository(db)
        return repo.find_by_user(user_id)

    def cancel_order(self, db: Session, order_id: str, user_id: str) -> Order:
        """Cancel an order if it is in a cancellable state."""
        order = self.get_order(db, order_id, user_id)
        allowed = self.VALID_TRANSITIONS.get(order.status, set())
        if "CANCELLED" not in allowed:
            raise OrderError(f"Order in status '{order.status}' cannot be cancelled")
        repo = OrderRepository(db)
        return repo.update_status(order, "CANCELLED")

    def advance_status(self, db: Session, order_id: str, new_status: str) -> Order:
        """Admin: advance order to the next valid status."""
        repo = OrderRepository(db)
        order = repo.find_by_id(order_id)
        if not order:
            raise OrderError(f"Order {order_id} not found")
        allowed = self.VALID_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise OrderError(
                f"Cannot transition from '{order.status}' to '{new_status}'"
            )
        return repo.update_status(order, new_status)


order_service = OrderService()
