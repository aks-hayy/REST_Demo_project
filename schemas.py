from pydantic import BaseModel, ConfigDict, ConfigDict, Field
from datetime import datetime


class ProductCreate(BaseModel):
    sku: str = Field(..., example="SKU12345")
    name: str = Field(..., example="Sample Product")
    price: float = Field(..., example=9.99)
    quantity: int = Field(..., example=100)
    is_active: bool = Field(..., example=True)


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    price: float
    quantity: int = Field(validation_alias="stock_qty")
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductUpdate(BaseModel):
    name: str | None = Field(None, example="Updated Product Name")
    price: float | None = Field(None, example=19.99)
    is_active: bool | None = Field(None, example=False)
    model_config = ConfigDict(extra="forbid")


class StockUpdate(BaseModel):
    quantity: int = Field(..., example=50)
    reason: str | None = Field(None, example="Restocking")
    model_config = ConfigDict(extra="forbid")


class OrderCreate(BaseModel):
    product_id: int = Field(..., example=1)
    status: str = Field(..., example="PAID")
    quantity: int = Field(..., example=2)
    model_config = ConfigDict(extra="forbid")


class OrderResponse(BaseModel):
    id: int
    status: str
    total_amount: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

