from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base

# --- Users (Buyers, Sellers, Vendors) ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_vendor = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# --- Vehicle Listings (AutoTrader concept) ---
class VehicleListing(Base):
    __tablename__ = "vehicle_listings"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    make = Column(String, index=True)
    model = Column(String, index=True)
    year = Column(Integer)
    price_sll = Column(Float)
    price_usd = Column(Float, nullable=True)
    mileage_km = Column(Integer)
    fuel_type = Column(String)
    transmission = Column(String)
    location = Column(String, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)     # <-- Fixed: was commented out
    is_sold = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    seller_id = Column(Integer, ForeignKey("users.id"))
    seller = relationship("User")


# --- Parts & Accessories (AutoZone concept) ---
class PartListing(Base):
    __tablename__ = "part_listings"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    compatible_make = Column(String, nullable=True)
    compatible_model = Column(String, nullable=True)
    price_sll = Column(Float)
    stock_quantity = Column(Integer, default=1)
    condition = Column(String)
    location = Column(String, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)     # <-- Fixed: was missing
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor_id = Column(Integer, ForeignKey("users.id"))
    vendor = relationship("User")


# --- Orders (For buying parts or paying vehicle deposits) ---
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"))
    total_amount_sll = Column(Float)
    status = Column(String, default="pending")
    payment_method = Column(String, nullable=True)
    payment_reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    buyer = relationship("User")

# --- Import Requests (Order parts from abroad) ---
class ImportRequest(Base):
    __tablename__ = "import_requests"
    id = Column(Integer, primary_key=True, index=True)
    
    # Customer info
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)  # WhatsApp number
    customer_email = Column(String, nullable=True)
    customer_location = Column(String, nullable=False)  # Freetown, Bo, etc.
    
    # Part requested
    part_name = Column(String, nullable=False)
    car_make = Column(String, nullable=False)
    car_model = Column(String, nullable=False)
    car_year = Column(String, nullable=False)
    part_number = Column(String, nullable=True)  # Optional OEM/aftermarket number
    quantity = Column(Integer, default=1)
    
    # Budget & urgency
    budget_sll = Column(Float, nullable=True)  # Optional customer budget
    urgency = Column(String, default="Normal")  # Normal, Urgent, Flexible
    
    # Notes
    notes = Column(Text, nullable=True)  # Additional details
    
    # Fulfillment tracking
    status = Column(String, default="pending")  # pending, quoted, ordered, shipped, delivered, cancelled
    quoted_price_sll = Column(Float, nullable=True)  # Price we quote back
    supplier_country = Column(String, nullable=True)  # Dubai, China, etc.
    estimated_days = Column(Integer, nullable=True)  # Delivery estimate
    
    # Admin notes
    admin_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# --- Supplier Catalog (Parts from Canada/abroad supplier sheets) ---
class SupplierCatalog(Base):
    __tablename__ = "supplier_catalog"
    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String, index=True, nullable=False)  # OEM/aftermarket number
    category = Column(String, index=True, nullable=True)       # e.g. "Ignition Coil"
    vehicle_compatibility = Column(String, nullable=True)      # e.g. "Corolla/Yaris"
    
    # Supplier brand #1
    brand_1 = Column(String, nullable=True)
    price_1_sll = Column(Float, nullable=True)
    price_1_cad = Column(Float, nullable=True)
    
    # Supplier brand #2
    brand_2 = Column(String, nullable=True)
    price_2_sll = Column(Float, nullable=True)
    price_2_cad = Column(Float, nullable=True)
    
    # Supplier brand #3
    brand_3 = Column(String, nullable=True)
    price_3_sll = Column(Float, nullable=True)
    price_3_cad = Column(Float, nullable=True)
    
    # Metadata
    in_stock = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
