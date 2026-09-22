from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.db import engine

FULFILLMENT_STATUSES = {"pending", "ordered_from_supplier", "shipped", "delivered", "cancelled"}


def create_part_order(
    *,
    buyer_id: str,
    supplier_part_id: str,
    quantity: int = 1,
    payment_method: str = "mobile_money",
    delivery_address: str = "",
    currency_code: str = "NLE",
    total_amount: str | None = None,
) -> dict[str, Any]:
    buyer_query = text("SELECT id FROM users WHERE id = CAST(:buyer_id AS uuid) AND role = 'buyer'")
    offer_query = text(
        """
        SELECT id, price, currency_code, stock
        FROM supplier_parts
        WHERE id = CAST(:supplier_part_id AS uuid)
        FOR UPDATE
        """
    )
    order_query = text(
        """
        INSERT INTO orders (buyer_id, payment_method, delivery_address, total_amount, currency_code)
        VALUES (CAST(:buyer_id AS uuid), CAST(:payment_method AS payment_method),
                :delivery_address, :total_amount, :currency_code)
        RETURNING id, status, total_amount, currency_code
        """
    )
    item_query = text(
        """
        INSERT INTO order_items (order_id, item_type, supplier_part_id, quantity, unit_price, currency_code)
        VALUES (:order_id, 'part', CAST(:supplier_part_id AS uuid), :quantity, :unit_price, :currency_code)
        """
    )

    with engine.begin() as connection:
        buyer = connection.execute(buyer_query, {"buyer_id": buyer_id}).scalar_one_or_none()
        if buyer is None:
            raise LookupError("Buyer was not found or is not registered as a buyer.")

        offer = connection.execute(offer_query, {"supplier_part_id": supplier_part_id}).mappings().one_or_none()
        if offer is None:
            raise LookupError("Supplier part was not found.")
        if offer["stock"] < quantity:
            raise LookupError("The requested quantity is not in stock.")

        amount = total_amount or str(offer["price"] * quantity)
        order = connection.execute(
            order_query,
            {
                "buyer_id": buyer_id,
                "payment_method": payment_method,
                "delivery_address": delivery_address,
                "total_amount": amount,
                "currency_code": offer["currency_code"],
            },
        ).mappings().one()
        connection.execute(
            item_query,
            {
                "order_id": order["id"],
                "supplier_part_id": supplier_part_id,
                "quantity": quantity,
                "unit_price": offer["price"],
                "currency_code": offer["currency_code"],
            },
        )

    return {
        "order_id": str(order["id"]),
        "buyer_id": str(buyer),
        "supplier_part_id": supplier_part_id,
        "quantity": quantity,
        "payment_method": payment_method,
        "delivery_address": delivery_address,
        "status": order["status"],
        "total_amount": str(order["total_amount"]),
        "currency_code": order["currency_code"].strip(),
    }


def confirm_order_payment(*, order_id: str, payment_reference: str) -> dict[str, Any]:
    query = text(
        """
        UPDATE orders
        SET payment_status = 'paid', status = 'confirmed'
        WHERE id = CAST(:order_id AS uuid)
          AND status = 'pending'
          AND payment_status = 'unpaid'
        RETURNING id, buyer_id, status, payment_status, total_amount, currency_code
        """
    )

    with engine.begin() as connection:
        order = connection.execute(query, {"order_id": order_id}).mappings().one_or_none()
    if order is None:
        raise LookupError("Order was not found or is not awaiting payment.")

    return {
        "order_id": str(order["id"]),
        "buyer_id": str(order["buyer_id"]),
        "status": order["status"],
        "payment_status": order["payment_status"],
        "payment_reference": payment_reference,
        "total_amount": str(order["total_amount"]),
        "currency_code": order["currency_code"].strip(),
    }


def get_part_order(*, order_id: str) -> dict[str, Any]:
    query = text(
        """
        SELECT o.id, o.buyer_id, o.status, o.payment_status, o.payment_method,
               o.delivery_address, o.total_amount, o.currency_code,
               oi.supplier_part_id, oi.quantity, oi.unit_price,
               oi.fulfillment_status, oi.estimated_delivery
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.id = CAST(:order_id AS uuid)
        ORDER BY oi.id
        LIMIT 1
        """
    )

    with engine.begin() as connection:
        order = connection.execute(query, {"order_id": order_id}).mappings().one_or_none()
    if order is None:
        raise LookupError("Order was not found.")

    return {
        "order_id": str(order["id"]),
        "buyer_id": str(order["buyer_id"]),
        "status": order["status"],
        "payment_status": order["payment_status"],
        "payment_method": order["payment_method"],
        "delivery_address": order["delivery_address"],
        "total_amount": str(order["total_amount"]),
        "currency_code": order["currency_code"].strip(),
        "item": {
            "supplier_part_id": str(order["supplier_part_id"]),
            "quantity": order["quantity"],
            "unit_price": str(order["unit_price"]),
            "fulfillment_status": order["fulfillment_status"],
            "estimated_delivery": order["estimated_delivery"].isoformat() if order["estimated_delivery"] else None,
        },
    }


def update_fulfillment_status(*, order_id: str, fulfillment_status: str) -> dict[str, Any]:
    if fulfillment_status not in FULFILLMENT_STATUSES:
        raise ValueError("Unsupported fulfillment status.")

    item_query = text(
        """
        UPDATE order_items
        SET fulfillment_status = CAST(:fulfillment_status AS fulfillment_status)
        WHERE order_id = CAST(:order_id AS uuid)
        RETURNING order_id, fulfillment_status
        """
    )
    order_query = text(
        """
        UPDATE orders
        SET status = CASE
            WHEN :fulfillment_status = 'delivered' THEN 'completed'::order_status
            WHEN :fulfillment_status = 'cancelled' THEN 'cancelled'::order_status
            ELSE status
        END
        WHERE id = CAST(:order_id AS uuid)
        RETURNING id, status, payment_status
        """
    )

    with engine.begin() as connection:
        item = connection.execute(
            item_query,
            {"order_id": order_id, "fulfillment_status": fulfillment_status},
        ).mappings().one_or_none()
        if item is None:
            raise LookupError("Order was not found.")
        order = connection.execute(
            order_query,
            {"order_id": order_id, "fulfillment_status": fulfillment_status},
        ).mappings().one()

    return {
        "order_id": str(order["id"]),
        "status": order["status"],
        "payment_status": order["payment_status"],
        "fulfillment_status": item["fulfillment_status"],
    }
