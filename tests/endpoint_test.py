import pytest
from fastapi import status
from sqlalchemy.orm import Session

from models import Product


@pytest.fixture
def sample_product_payload():
    return {
        "sku": "SKU-100",
        "name": "Mechanical Keyboard",
        "price": 99.99,
        "quantity": 15,
        "is_active": True,
    }


def test_create_product(client, db_session: Session, sample_product_payload):

    response = client.post("/products", json=sample_product_payload)
    assert response.status_code == status.HTTP_201_CREATED
    created_product = (
        db_session.query(Product).filter_by(sku=sample_product_payload["sku"]).first()
    )
    assert created_product is not None
    assert created_product.name == sample_product_payload["name"]
    assert float(created_product.price) == sample_product_payload["price"]
    assert created_product.stock_qty == sample_product_payload["quantity"]


def test_create_product_duplicate_sku(
    client, db_session: Session, sample_product_payload
):
    response1 = client.post("/products", json=sample_product_payload)
    assert response1.status_code == status.HTTP_201_CREATED
    response2 = client.post("/products", json=sample_product_payload)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert response2.json()["detail"] == "Product with this SKU already exists."


def test_order_reduces_stock(client, db_session: Session, sample_product_payload):
    response = client.post("/products", json=sample_product_payload)
    assert response.status_code == status.HTTP_201_CREATED
    product_id = response.json()["id"]
    order_payload = {"product_id": product_id, "status": "PAID", "quantity": 5}
    order_response = client.post("/orders", json=order_payload)
    assert order_response.status_code == status.HTTP_201_CREATED
    updated_product = db_session.query(Product).filter_by(id=product_id).first()
    assert (
        updated_product.stock_qty
        == sample_product_payload["quantity"] - order_payload["quantity"]
    )


def test_order_insufficient_stock(client, db_session: Session, sample_product_payload):
    response = client.post("/products", json=sample_product_payload)
    assert response.status_code == status.HTTP_201_CREATED
    product_id = response.json()["id"]
    order_payload = {"product_id": product_id, "status": "PAID", "quantity": 20}
    order_response = client.post("/orders", json=order_payload)
    assert order_response.status_code == status.HTTP_400_BAD_REQUEST
    assert order_response.json()["detail"] == "Insufficient stock."
    updated_product = db_session.query(Product).filter_by(id=product_id).first()
    assert updated_product.stock_qty == sample_product_payload["quantity"]


def test_order_cancellation_restores_stock(
    client, db_session: Session, sample_product_payload
):
    response = client.post("/products", json=sample_product_payload)
    assert response.status_code == status.HTTP_201_CREATED
    product_id = response.json()["id"]
    order_payload = {"product_id": product_id, "status": "PAID", "quantity": 5}
    order_response = client.post("/orders", json=order_payload)
    assert order_response.status_code == status.HTTP_201_CREATED
    order_id = order_response.json()["id"]
    cancel_response = client.post(f"/orders/{order_id}/cancel")
    assert cancel_response.status_code == status.HTTP_200_OK
    updated_product = db_session.query(Product).filter_by(id=product_id).first()
    assert updated_product.stock_qty == sample_product_payload["quantity"]


def test_stock_update(client, db_session: Session, sample_product_payload):
    response = client.post("/products", json=sample_product_payload)
    assert response.status_code == status.HTTP_201_CREATED
    product_id = response.json()["id"]
    stock_update_payload = {"quantity": 10, "reason": "Restocking"}
    stock_response = client.post(
        f"/products/{product_id}/stock-adjustments", json=stock_update_payload
    )
    assert stock_response.status_code == status.HTTP_200_OK
    updated_product = db_session.query(Product).filter_by(id=product_id).first()
    assert (
        updated_product.stock_qty
        == sample_product_payload["quantity"] + stock_update_payload["quantity"]
    )


def test_stock_update_prevents_negative_stock(client, sample_product_payload):
    response = client.post("/products", json=sample_product_payload)
    product_id = response.json()["id"]
    stock_response = client.post(
        f"/products/{product_id}/stock-adjustments",
        json={"quantity": -20},
    )
    assert stock_response.status_code == status.HTTP_400_BAD_REQUEST
    assert stock_response.json()["detail"] == "Stock quantity cannot be negative."


def test_list_products_search_and_boolean_filters(client):
    products = [
        {
            "sku": "KEY-01",
            "name": "Mechanical Keyboard",
            "price": 99.99,
            "quantity": 10,
            "is_active": True,
        },
        {
            "sku": "KEY-02",
            "name": "Membrane Keyboard",
            "price": 29.99,
            "quantity": 15,
            "is_active": False,
        },
        {
            "sku": "MOU-01",
            "name": "Wireless Mouse",
            "price": 49.99,
            "quantity": 20,
            "is_active": True,
        },
    ]
    for item in products:
        client.post("/products", json=item)
    search_res = client.get("/products", params={"search": "keyboard"})
    assert search_res.status_code == 200
    assert len(search_res.json()) == 2
    inactive_res = client.get("/products", params={"is_active": False})
    assert inactive_res.status_code == 200
    inactive_data = inactive_res.json()
    assert len(inactive_data) == 1
    assert inactive_data[0]["sku"] == "KEY-02"
    combined_res = client.get(
        "/products", params={"search": "keyboard", "is_active": True}
    )
    assert combined_res.status_code == 200
    combined_data = combined_res.json()
    assert len(combined_data) == 1
    assert combined_data[0]["sku"] == "KEY-01"
