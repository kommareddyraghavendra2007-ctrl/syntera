"""Order management API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.auth.dependencies import get_admin_user, get_current_user
from src.database.connection import get_db
from src.database.models import User
from src.orders import OrderError, order_service

router = APIRouter(prefix="/orders", tags=["orders"])


class CreateOrderRequest(BaseModel):
    items: list[dict]
    shipping_address: str | None = None


class AdvanceStatusRequest(BaseModel):
    new_status: str


@router.get("")
def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all orders for the current user."""
    orders = order_service.get_user_orders(db, current_user.id)
    return [
        {
            "id": o.id,
            "status": o.status,
            "total": str(o.total_amount),
            "created_at": str(o.created_at),
        }
        for o in orders
    ]


@router.post("", status_code=201)
def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new order for the current user."""
    try:
        order = order_service.create_order(
            db, current_user.id, body.items, body.shipping_address
        )
        return {"id": order.id, "status": order.status, "total": str(order.total_amount)}
    except OrderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{order_id}")
def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific order by ID."""
    try:
        order = order_service.get_order(db, order_id, current_user.id)
        return {
            "id": order.id,
            "status": order.status,
            "total": str(order.total_amount),
            "shipping_address": order.shipping_address,
            "items": [
                {
                    "product_id": i.product_id,
                    "quantity": i.quantity,
                    "unit_price": str(i.unit_price),
                    "subtotal": str(i.subtotal),
                }
                for i in order.items
            ],
        }
    except OrderError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an order if it is in a cancellable state."""
    try:
        order = order_service.cancel_order(db, order_id, current_user.id)
        return {"id": order.id, "status": order.status}
    except OrderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{order_id}/status")
def advance_order_status(
    order_id: str,
    body: AdvanceStatusRequest,
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Admin only: advance order to the next valid status."""
    try:
        order = order_service.advance_status(db, order_id, body.new_status)
        return {"id": order.id, "status": order.status}
    except OrderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
