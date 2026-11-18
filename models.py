from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    DECIMAL,
    CheckConstraint,
    Boolean,
    Enum,
    ForeignKey,
    func,
)

from database import Base


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(DECIMAL(10, 2), CheckConstraint("price > 0"), nullable=False)
    stock_qty = Column(Integer, CheckConstraint("stock_qty >= 0"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    reason = Column(
        String, default="Original Stock"
    )  # reason for restocking defaulted to original stock


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    status = Column(Enum("PAID", "CANCELLED"))
    total_amount = Column(DECIMAL(10, 2))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, CheckConstraint("quantity > 0"))
    unit_price = Column(DECIMAL(10, 2))
    line_total = Column(
        DECIMAL(10, 2),
        CheckConstraint("line_total = quantity * unit_price"),
    )
