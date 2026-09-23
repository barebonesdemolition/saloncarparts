import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"


class PartType(str, enum.Enum):
    OEM = "oem"
    AFTERMARKET = "aftermarket"


class ListingCondition(str, enum.Enum):
    NEW = "new"
    USED = "used"
    SALVAGE = "salvage"


class ListingStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    WITHDRAWN = "withdrawn"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    MOBILE_MONEY = "mobile_money"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    CARD = "card"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"


class OrderItemType(str, enum.Enum):
    PART = "part"
    LISTING = "listing"


class FulfillmentStatus(str, enum.Enum):
    PENDING = "pending"
    ORDERED_FROM_SUPPLIER = "ordered_from_supplier"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


def _enum_type(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_class, name=name, values_callable=lambda values: [item.value for item in values])


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(_enum_type(UserRole, "user_role"), nullable=False, server_default=text("'buyer'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    cars: Mapped[List["Car"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    listings: Mapped[List["Listing"]] = relationship(back_populates="seller")
    orders: Mapped[List["Order"]] = relationship(back_populates="buyer")


class Car(Base):
    __tablename__ = "user_cars"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vin: Mapped[str] = mapped_column(CHAR(17), unique=True, nullable=False)
    make: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    trim: Mapped[str] = mapped_column(Text, nullable=True)
    engine: Mapped[str] = mapped_column(Text, nullable=True)
    user: Mapped[User] = relationship(back_populates="cars")


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (CheckConstraint("year_to >= year_from", name="vehicles_year_range"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    make: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    year_from: Mapped[int] = mapped_column(Integer, nullable=False)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False)
    engine: Mapped[str] = mapped_column(Text, nullable=True)
    body_type: Mapped[str] = mapped_column(Text, nullable=True)
    vin_patterns: Mapped[List["VinPattern"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    fitments: Mapped[List["PartFitment"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    listings: Mapped[List["Listing"]] = relationship(back_populates="vehicle")


class VinPattern(Base):
    __tablename__ = "vin_patterns"
    __table_args__ = (
        CheckConstraint("char_length(wmi) = 3", name="vin_patterns_wmi_len"),
        CheckConstraint("char_length(vds_pattern) = 5", name="vin_patterns_vds_len"),
        UniqueConstraint("wmi", "vds_pattern", "vehicle_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    wmi: Mapped[str] = mapped_column(Text, nullable=False)
    vds_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    vehicle: Mapped[Vehicle] = relationship(back_populates="vin_patterns")


class Part(Base):
    __tablename__ = "parts"
    __table_args__ = (UniqueConstraint("brand", "part_number", name="parts_brand_number_unique"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    part_number: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    part_type: Mapped[PartType] = mapped_column(_enum_type(PartType, "part_type"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    fitments: Mapped[List["PartFitment"]] = relationship(back_populates="part", cascade="all, delete-orphan")
    supplier_parts: Mapped[List["SupplierPart"]] = relationship(back_populates="part", cascade="all, delete-orphan")
    alternatives: Mapped[List["PartAlternative"]] = relationship(foreign_keys="PartAlternative.part_id", back_populates="part", cascade="all, delete-orphan")
    alternative_for: Mapped[List["PartAlternative"]] = relationship(foreign_keys="PartAlternative.alternative_part_id", back_populates="alternative_part", cascade="all, delete-orphan")


class PartFitment(Base):
    __tablename__ = "part_fitments"
    __table_args__ = (
        CheckConstraint("year_to >= year_from", name="part_fitments_year_range"),
        UniqueConstraint("part_id", "vehicle_id", "year_from", name="part_fitments_unique"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    part_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    year_from: Mapped[int] = mapped_column(Integer, nullable=False)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    part: Mapped[Part] = relationship(back_populates="fitments")
    vehicle: Mapped[Vehicle] = relationship(back_populates="fitments")


class PartAlternative(Base):
    __tablename__ = "part_alternatives"
    __table_args__ = (
        CheckConstraint("part_id <> alternative_part_id", name="part_alternatives_not_self"),
        UniqueConstraint("part_id", "alternative_part_id", name="part_alternatives_unique"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    part_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    alternative_part_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    part: Mapped[Part] = relationship(foreign_keys=[part_id], back_populates="alternatives")
    alternative_part: Mapped[Part] = relationship(foreign_keys=[alternative_part_id], back_populates="alternative_for")


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    supplier_parts: Mapped[List["SupplierPart"]] = relationship(back_populates="supplier", cascade="all, delete-orphan")


class SupplierPart(Base):
    __tablename__ = "supplier_parts"
    __table_args__ = (
        UniqueConstraint("supplier_id", "part_id", name="supplier_parts_unique"),
        CheckConstraint("price >= 0", name="supplier_parts_price_nonneg"),
        CheckConstraint("stock >= 0", name="supplier_parts_stock_nonneg"),
        CheckConstraint("lead_time_days >= 0", name="supplier_parts_lead_nonneg"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="supplier_parts_currency_fmt"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    part_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    supplier: Mapped[Supplier] = relationship(back_populates="supplier_parts")
    part: Mapped[Part] = relationship(back_populates="supplier_parts")
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="supplier_part")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("price >= 0", name="listings_price_nonneg"),
        CheckConstraint("mileage_km IS NULL OR mileage_km >= 0", name="listings_mileage_nonneg"),
        CheckConstraint("vin IS NULL OR char_length(vin) = 17", name="listings_vin_len"),
        CheckConstraint("vin IS NULL OR vin ~ '^[A-HJ-NPR-Z0-9]{17}$'", name="listings_vin_chars"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="listings_currency_fmt"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True)
    vin: Mapped[str] = mapped_column(Text, unique=True, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    condition: Mapped[ListingCondition] = mapped_column(_enum_type(ListingCondition, "listing_condition"), nullable=False)
    mileage_km: Mapped[int] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ListingStatus] = mapped_column(_enum_type(ListingStatus, "listing_status"), nullable=False, server_default=text("'draft'"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    seller: Mapped[User] = relationship(back_populates="listings")
    vehicle: Mapped[Vehicle] = relationship(back_populates="listings")
    photos: Mapped[List["ListingPhoto"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="listing")


class ListingPhoto(Base):
    __tablename__ = "listing_photos"
    __table_args__ = (UniqueConstraint("listing_id", "position"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    listing: Mapped[Listing] = relationship(back_populates="photos")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(_enum_type(OrderStatus, "order_status"), nullable=False, server_default=text("'pending'"))
    payment_method: Mapped[PaymentMethod] = mapped_column(_enum_type(PaymentMethod, "payment_method"), nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(_enum_type(PaymentStatus, "payment_status"), nullable=False, server_default=text("'unpaid'"))
    delivery_address: Mapped[str] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    buyer: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_items_quantity_pos"),
        CheckConstraint("unit_price >= 0", name="order_items_price_nonneg"),
        CheckConstraint("(item_type = 'part' AND supplier_part_id IS NOT NULL AND listing_id IS NULL) OR (item_type = 'listing' AND listing_id IS NOT NULL AND supplier_part_id IS NULL)", name="order_items_one_target"),
        CheckConstraint("item_type <> 'listing' OR quantity = 1", name="order_items_listing_qty"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type: Mapped[OrderItemType] = mapped_column(_enum_type(OrderItemType, "order_item_type"), nullable=False)
    supplier_part_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supplier_parts.id", ondelete="RESTRICT"), nullable=True, index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    estimated_delivery: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfillment_status: Mapped[FulfillmentStatus] = mapped_column(_enum_type(FulfillmentStatus, "fulfillment_status"), nullable=False, server_default=text("'pending'"))
    order: Mapped[Order] = relationship(back_populates="items")
    supplier_part: Mapped[SupplierPart] = relationship(back_populates="order_items")
    listing: Mapped[Listing] = relationship(back_populates="order_items")