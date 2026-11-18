from fastapi import FastAPI, Query, status, Depends, HTTPException
from sqlalchemy import func
from auth import verify_api_key
from database import Base, engine, get_session
from models import Product, Order, OrderItem
from schemas import (
    OrderResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    StockUpdate,
    OrderCreate,
)
from sqlalchemy.exc import IntegrityError

Base.metadata.create_all(bind=engine)
app = FastAPI(dependencies=[Depends(verify_api_key)])


@app.get("/")
def root():
    return {"message": "POS API is running"}


@app.post(
    "/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
def create_product(product: ProductCreate, Session=Depends(get_session)):
    db_product = Product(
        sku=product.sku,
        name=product.name,
        price=product.price,
        stock_qty=product.quantity,
        is_active=product.is_active,
    )
    try:
        Session.add(db_product)
        Session.commit()
        Session.refresh(db_product)
    except IntegrityError:
        Session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this SKU already exists.",
        )

    return db_product


@app.get(
    "/products", response_model=list[ProductResponse], status_code=status.HTTP_200_OK
)
def get_products(
    Session=Depends(get_session),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=50),
    is_active: bool | None = Query(None),
):
    query = Session.query(Product)
    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%")
        )
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    products = query.offset((page - 1) * size).limit(size).all()
    if not products:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No products found.",
        )
    return products


@app.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def get_product(product_id: int, Session=Depends(get_session)):
    product = Session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product


@app.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def update_product(
    product_id: int, product_update: ProductUpdate, Session=Depends(get_session)
):
    product = Session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    for field, value in product_update.dict(exclude_unset=True).items():
        setattr(product, field, value)
    Session.commit()
    Session.refresh(product)
    return product


@app.post("/products/{product_id}/stock-adjustments", response_model=StockUpdate)
def create_stock_adjustment(
    stock_update: StockUpdate, product_id: int, Session=Depends(get_session)
):
    product = Session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    product.stock_qty += stock_update.quantity
    product.reason = stock_update.reason

    if product.stock_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock quantity cannot be negative.",
        )
    Session.commit()
    Session.refresh(product)
    return stock_update


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_create: OrderCreate, Session=Depends(get_session)):
    product = Session.get(Product, order_create.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    if product.stock_qty < order_create.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock.",
        )
    price = product.price
    total_amount = price * order_create.quantity
    product.stock_qty -= order_create.quantity
    n_order = Order(status=order_create.status, total_amount=total_amount)
    Session.add(n_order)
    Session.flush()

    order_item = OrderItem(
        order_id=n_order.id,
        product_id=product.id,
        quantity=order_create.quantity,
        unit_price=price,
        line_total=total_amount,
    )
    Session.add(order_item)
    Session.commit()

    Session.refresh(n_order)
    return n_order


@app.get("/orders/{order_id}")
def get_orders(order_id: int, Session=Depends(get_session)):
    order = Session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, Session=Depends(get_session)):
    order = Session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or already canceled.",
        )
    if order.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is already canceled.",
        )
    order.status = "CANCELLED"
    O_item = Session.query(OrderItem).filter(OrderItem.order_id == order.id).first()
    product = Session.get(Product, O_item.product_id)
    product.stock_qty += O_item.quantity
    Session.commit()
    Session.refresh(order)
    Session.refresh(product)
    return {"message": f"Order {order_id} has been canceled."}


@app.get("/reports/daily-sales")
def get_daily_sales(t_date: str, Session=Depends(get_session)):
    orders = (
        Session.query(Order)
        .filter(func.DATE(Order.created_at) == t_date)
        .filter(Order.status == "PAID")
        .all()
    )
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sales found for the specified date.",
        )
    total_sales = sum(order.total_amount for order in orders)
    order_ids = [order.id for order in orders]
    t_3 = (
        Session.query(
            OrderItem.product_id, func.sum(OrderItem.quantity).label("total_quantity")
        )
        .filter(OrderItem.order_id.in_(order_ids))
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(3)
        .all()
    )
    t_3_list = [
        {"product_id": row.product_id, "total_quantity": row.total_quantity}
        for row in t_3
    ]
    sales = {"total_sales": total_sales, "top_3_products": t_3_list}

    return {"message": f"Daily sales for {t_date}", "sales": sales}
