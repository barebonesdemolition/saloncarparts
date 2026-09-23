-- Salon AutoZone & AutoTrader Unified Schema
-- Target: PostgreSQL 13+

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enums
CREATE TYPE user_role AS ENUM ('buyer', 'seller', 'dealer_admin', 'platform_admin');
CREATE TYPE part_type AS ENUM ('oem', 'aftermarket');
CREATE TYPE listing_condition AS ENUM ('new', 'used', 'certified_pre_owned', 'salvage');
CREATE TYPE listing_status AS ENUM ('draft', 'active', 'reserved', 'sold', 'withdrawn');
CREATE TYPE price_badge AS ENUM ('great_price', 'good_price', 'fair_price', 'above_market');
CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'completed', 'cancelled');
CREATE TYPE payment_method AS ENUM ('mobile_money', 'bank_transfer', 'cash', 'card');
CREATE TYPE payment_status AS ENUM ('unpaid', 'paid', 'refunded');
CREATE TYPE order_item_type AS ENUM ('part', 'listing');
CREATE TYPE fulfillment_type AS ENUM ('ship_to_address', 'store_pickup');
CREATE TYPE fulfillment_status AS ENUM ('pending', 'ordered_from_supplier', 'shipped', 'ready_for_pickup', 'delivered', 'cancelled');
CREATE TYPE inquiry_type AS ENUM ('general_question', 'test_drive_request', 'financing_inquiry', 'trade_in_appraisal');

-- 1. User Management
CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name text NOT NULL,
    phone text NOT NULL UNIQUE,
    email text UNIQUE,
    hashed_password text,
    role user_role NOT NULL DEFAULT 'buyer',
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Saved Garage (AutoZone style fitment selector)
CREATE TABLE user_cars (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    vin char(17) NOT NULL,
    nickname text,
    make text NOT NULL,
    model text NOT NULL,
    year integer NOT NULL,
    trim text,
    engine text,
    is_primary boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT user_cars_vin_chars CHECK (vin ~ '^[A-HJ-NPR-Z0-9]{17}$')
);

CREATE INDEX user_cars_user_idx ON user_cars (user_id);

-- 3. Vehicle Catalog & VIN Decoding
CREATE TABLE vehicles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    make text NOT NULL,
    model text NOT NULL,
    year_from integer NOT NULL,
    year_to integer NOT NULL,
    body_type text NOT NULL,
    engine text,
    transmission text,
    drivetrain text,
    is_active boolean NOT NULL DEFAULT true,
    CONSTRAINT vehicles_year_range CHECK (year_to >= year_from)
);

CREATE INDEX vehicles_lookup_idx ON vehicles (make, model, year_from, year_to);

CREATE TABLE vin_patterns (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id uuid NOT NULL REFERENCES vehicles (id) ON DELETE CASCADE,
    wmi text NOT NULL,
    vds_pattern text NOT NULL,
    CONSTRAINT vin_patterns_wmi_len CHECK (char_length(wmi) = 3),
    CONSTRAINT vin_patterns_vds_len CHECK (char_length(vds_pattern) = 5),
    UNIQUE (wmi, vds_pattern, vehicle_id)
);

CREATE INDEX vin_patterns_lookup_idx ON vin_patterns (wmi, vds_pattern);

-- 4. AutoZone Auto Parts Catalog
CREATE TABLE parts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    part_number text NOT NULL,
    brand text NOT NULL,
    name text NOT NULL,
    category text NOT NULL,
    part_type part_type NOT NULL,
    description text,
    is_active boolean NOT NULL DEFAULT true,
    CONSTRAINT parts_brand_number_unique UNIQUE (brand, part_number)
);

CREATE INDEX parts_category_idx ON parts (category);
CREATE INDEX parts_search_idx ON parts (name, part_number, brand);

CREATE TABLE part_fitments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id uuid NOT NULL REFERENCES parts (id) ON DELETE CASCADE,
    vehicle_id uuid NOT NULL REFERENCES vehicles (id) ON DELETE CASCADE,
    year_from integer NOT NULL,
    year_to integer NOT NULL,
    fitment_notes text,
    CONSTRAINT part_fitments_year_range CHECK (year_to >= year_from),
    CONSTRAINT part_fitments_unique UNIQUE (part_id, vehicle_id, year_from)
);

CREATE INDEX part_fitments_vehicle_idx ON part_fitments (vehicle_id);
CREATE INDEX part_fitments_part_idx ON part_fitments (part_id);

-- Strict ordering constraint (part_id < alternative_part_id) prevents symmetric duplication
CREATE TABLE part_alternatives (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id uuid NOT NULL REFERENCES parts (id) ON DELETE CASCADE,
    alternative_part_id uuid NOT NULL REFERENCES parts (id) ON DELETE CASCADE,
    CONSTRAINT part_alternatives_ordering CHECK (part_id < alternative_part_id),
    CONSTRAINT part_alternatives_unique UNIQUE (part_id, alternative_part_id)
);

CREATE INDEX part_alternatives_alt_idx ON part_alternatives (alternative_part_id);

-- 5. Suppliers & AutoZone Pickup Locations
CREATE TABLE suppliers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    store_code text UNIQUE,
    location_address text NOT NULL,
    city text NOT NULL,
    contact_phone text,
    contact_email text,
    allows_pickup boolean NOT NULL DEFAULT true,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE supplier_parts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id uuid NOT NULL REFERENCES suppliers (id) ON DELETE CASCADE,
    part_id uuid NOT NULL REFERENCES parts (id) ON DELETE CASCADE,
    price numeric(12,2) NOT NULL,
    currency_code char(3) NOT NULL DEFAULT 'CAD',
    stock integer NOT NULL DEFAULT 0,
    lead_time_days integer NOT NULL DEFAULT 0,
    CONSTRAINT supplier_parts_unique UNIQUE (supplier_id, part_id),
    CONSTRAINT supplier_parts_price_nonneg CHECK (price >= 0),
    CONSTRAINT supplier_parts_stock_nonneg CHECK (stock >= 0),
    CONSTRAINT supplier_parts_lead_nonneg CHECK (lead_time_days >= 0),
    CONSTRAINT supplier_parts_currency_fmt CHECK (currency_code ~ '^[A-Z]{3}$')
);

CREATE INDEX supplier_parts_part_idx ON supplier_parts (part_id);
CREATE INDEX supplier_parts_in_stock_idx ON supplier_parts (part_id) WHERE stock > 0;

-- 6. AutoTrader Vehicle Listings
CREATE TABLE listings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    vehicle_id uuid NOT NULL REFERENCES vehicles (id) ON DELETE RESTRICT,
    vin text,
    title text NOT NULL,
    price numeric(12,2) NOT NULL,
    currency_code char(3) NOT NULL DEFAULT 'CAD',
    market_price_badge price_badge,
    condition listing_condition NOT NULL DEFAULT 'used',
    mileage_km integer NOT NULL,
    exterior_color text,
    interior_color text,
    fuel_type text,
    description text,
    status listing_status NOT NULL DEFAULT 'draft',
    is_featured boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT listings_price_nonneg CHECK (price >= 0),
    CONSTRAINT listings_mileage_nonneg CHECK (mileage_km >= 0),
    CONSTRAINT listings_vin_len CHECK (vin IS NULL OR char_length(vin) = 17),
    CONSTRAINT listings_vin_chars CHECK (vin IS NULL OR vin ~ '^[A-HJ-NPR-Z0-9]{17}$'),
    CONSTRAINT listings_currency_fmt CHECK (currency_code ~ '^[A-Z]{3}$')
);

CREATE INDEX listings_status_idx ON listings (status);
CREATE INDEX listings_vehicle_idx ON listings (vehicle_id);
CREATE INDEX listings_seller_idx ON listings (seller_id);
CREATE INDEX listings_search_idx ON listings (status, price, mileage_km, created_at DESC);

-- Partial Unique Index: Prevents active duplicates, but allows re-listing previously sold/withdrawn VINs
CREATE UNIQUE INDEX listings_active_vin_idx 
    ON listings (vin) 
    WHERE status IN ('active', 'reserved') AND vin IS NOT NULL;

CREATE TABLE listing_photos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id uuid NOT NULL REFERENCES listings (id) ON DELETE CASCADE,
    url text NOT NULL,
    position integer NOT NULL DEFAULT 0,
    is_hero boolean NOT NULL DEFAULT false,
    UNIQUE (listing_id, position)
);

-- 7. AutoTrader Marketplace Inquiries & Lead Generation
CREATE TABLE listing_inquiries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id uuid NOT NULL REFERENCES listings (id) ON DELETE CASCADE,
    buyer_id uuid REFERENCES users (id) ON DELETE SET NULL,
    inquiry_type inquiry_type NOT NULL DEFAULT 'general_question',
    buyer_name text NOT NULL,
    buyer_email text NOT NULL,
    buyer_phone text NOT NULL,
    message text NOT NULL,
    is_resolved boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX listing_inquiries_listing_idx ON listing_inquiries (listing_id);

-- 8. Orders & Checkout (Parts & Vehicle Deposits)
CREATE TABLE orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    status order_status NOT NULL DEFAULT 'pending',
    payment_method payment_method NOT NULL,
    payment_status payment_status NOT NULL DEFAULT 'unpaid',
    delivery_address text,
    total_amount numeric(12,2) NOT NULL DEFAULT 0,
    currency_code char(3) NOT NULL DEFAULT 'CAD',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT orders_total_nonneg CHECK (total_amount >= 0),
    CONSTRAINT orders_currency_fmt CHECK (currency_code ~ '^[A-Z]{3}$')
);

CREATE INDEX orders_buyer_idx ON orders (buyer_id);

CREATE TABLE order_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    item_type order_item_type NOT NULL,
    supplier_part_id uuid REFERENCES supplier_parts (id) ON DELETE RESTRICT,
    listing_id uuid REFERENCES listings (id) ON DELETE RESTRICT,
    fulfillment_type fulfillment_type NOT NULL DEFAULT 'ship_to_address',
    pickup_supplier_id uuid REFERENCES suppliers (id) ON DELETE RESTRICT,
    quantity integer NOT NULL DEFAULT 1,
    unit_price numeric(12,2) NOT NULL,
    currency_code char(3) NOT NULL DEFAULT 'CAD',
    estimated_delivery timestamptz,
    fulfillment_status fulfillment_status NOT NULL DEFAULT 'pending',
    CONSTRAINT order_items_quantity_pos CHECK (quantity > 0),
    CONSTRAINT order_items_price_nonneg CHECK (unit_price >= 0),
    CONSTRAINT order_items_currency_fmt CHECK (currency_code ~ '^[A-Z]{3}$'),
    CONSTRAINT order_items_one_target CHECK (
        (item_type = 'part' AND supplier_part_id IS NOT NULL AND listing_id IS NULL) OR
        (item_type = 'listing' AND listing_id IS NOT NULL AND supplier_part_id IS NULL)
    ),
    CONSTRAINT order_items_listing_qty CHECK (item_type <> 'listing' OR quantity = 1)
);

CREATE INDEX order_items_order_idx ON order_items (order_id);
CREATE INDEX order_items_supplier_part_idx ON order_items (supplier_part_id) WHERE supplier_part_id IS NOT NULL;

CREATE UNIQUE INDEX order_items_listing_active_unique
    ON order_items (listing_id)
    WHERE listing_id IS NOT NULL AND fulfillment_status <> 'cancelled';

-- 9. AutoZone Exact-Fit Part Recommendation View
CREATE VIEW v_autozone_part_fitments AS
SELECT
    pf.vehicle_id,
    p.id AS part_id,
    p.part_number,
    p.brand,
    p.name AS part_name,
    p.category,
    p.part_type,
    pf.fitment_notes,
    sp.id AS supplier_part_id,
    s.id AS supplier_id,
    s.name AS supplier_name,
    s.city AS store_city,
    s.allows_pickup,
    sp.price,
    sp.currency_code,
    sp.stock,
    sp.lead_time_days,
    CASE
        WHEN sp.stock > 0 THEN 'IN_STOCK'
        ELSE 'AVAILABLE_TO_ORDER'
    END AS availability_status,
    ROW_NUMBER() OVER (
        PARTITION BY pf.vehicle_id, p.id
        ORDER BY sp.stock DESC, sp.price ASC
    ) AS best_option_rank
FROM part_fitments pf
JOIN parts p ON p.id = pf.part_id
JOIN supplier_parts sp ON sp.part_id = p.id
JOIN suppliers s ON s.id = sp.supplier_id
WHERE p.is_active = true AND s.is_active = true;

-- 10. Triggers for Currency Consistency
CREATE FUNCTION order_items_check_currency() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    order_currency char(3);
BEGIN
    SELECT currency_code INTO order_currency
    FROM orders
    WHERE id = NEW.order_id
    FOR SHARE;

    IF NEW.currency_code <> order_currency THEN
        RAISE EXCEPTION
            'order item currency (%) does not match order % currency (%)',
            NEW.currency_code, NEW.order_id, order_currency
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER order_items_currency_match
    BEFORE INSERT OR UPDATE OF currency_code, order_id ON order_items
    FOR EACH ROW
    EXECUTE FUNCTION order_items_check_currency();

COMMIT;