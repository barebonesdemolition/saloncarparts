-- Salon AutoZone seed data
-- Run after schema.sql. Safe to re-run against a fresh schema only
-- (fixed UUIDs will collide with themselves if seeded twice).

BEGIN;

INSERT INTO users (id, full_name, phone, email, role) VALUES
    ('10000000-0000-0000-0000-000000000001', 'Abu Kamara', '+23276123001', 'abu.kamara@example.com', 'seller'),
    ('10000000-0000-0000-0000-000000000002', 'Fatmata Sesay', '+23276123002', 'fatmata.sesay@example.com', 'seller'),
    ('10000000-0000-0000-0000-000000000003', 'Mohamed Bangura', '+23276123003', 'mohamed.bangura@example.com', 'buyer'),
    ('10000000-0000-0000-0000-000000000004', 'Isata Koroma', '+23276123004', 'isata.koroma@example.com', 'buyer'),
    ('10000000-0000-0000-0000-000000000005', 'Admin User', '+23276123005', 'admin@saloneparts.sl', 'admin');

INSERT INTO vehicles (id, make, model, year_from, year_to, engine, body_type) VALUES
    ('20000000-0000-0000-0000-000000000001', 'Toyota', 'Corolla', 2003, 2008, '1.8L 1ZZ-FE', 'sedan'),
    ('20000000-0000-0000-0000-000000000002', 'Toyota', 'Corolla', 2009, 2013, '1.8L 2ZR-FE', 'sedan'),
    ('20000000-0000-0000-0000-000000000003', 'Toyota', 'Hilux', 2005, 2015, '2.5L 2KD-FTV', 'pickup'),
    ('20000000-0000-0000-0000-000000000004', 'Nissan', 'Almera', 2000, 2006, '1.6L QG16', 'sedan'),
    ('20000000-0000-0000-0000-000000000005', 'Honda', 'CR-V', 2007, 2011, '2.4L K24Z1', 'suv');

INSERT INTO vin_patterns (id, vehicle_id, wmi, vds_pattern) VALUES
    ('21000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'JTD', 'BR32E'),
    ('21000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000002', 'JTD', 'BT40E'),
    ('21000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000003', 'MR0', 'KZN15'),
    ('21000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000004', 'JN1', 'BN15A'),
    ('21000000-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000005', 'JHL', 'RE4H8');

INSERT INTO suppliers (id, name, location, contact_phone, contact_email, is_active) VALUES
    ('30000000-0000-0000-0000-000000000001', 'Freetown Auto Parts', 'Freetown, Wellington', '+23278300001', 'sales@freetownautoparts.sl', true),
    ('30000000-0000-0000-0000-000000000002', 'Bo Motor Spares', 'Bo, Kandeh Town', '+23278300002', 'info@bomotorspares.sl', true),
    ('30000000-0000-0000-0000-000000000003', 'Kissy Import & Export', 'Freetown, Kissy', '+23278300003', 'kissyimportexport@example.com', true),
    ('30000000-0000-0000-0000-000000000004', 'Makeni Parts Depot', 'Makeni', '+23278300004', 'contact@makeniparts.sl', false);

INSERT INTO parts (id, part_number, brand, name, category, part_type, description) VALUES
    ('40000000-0000-0000-0000-000000000001', '04465-02220', 'Toyota', 'Front brake pad set', 'brakes', 'oem', 'OEM front brake pads for Corolla/Hilux platforms'),
    ('40000000-0000-0000-0000-000000000002', 'GDB3216', 'TRW', 'Front brake pad set', 'brakes', 'aftermarket', 'Aftermarket equivalent front brake pads'),
    ('40000000-0000-0000-0000-000000000003', '90915-YZZD2', 'Toyota', 'Oil filter', 'engine', 'oem', 'OEM spin-on oil filter'),
    ('40000000-0000-0000-0000-000000000004', 'W610/3', 'Mann', 'Oil filter', 'engine', 'aftermarket', 'Aftermarket oil filter, common cross-reference'),
    ('40000000-0000-0000-0000-000000000005', '48touch-1', 'Toyota', 'Front shock absorber', 'suspension', 'oem', 'OEM front strut assembly'),
    ('40000000-0000-0000-0000-000000000006', '28113-2W000', 'Hyundai', 'Cabin air filter', 'hvac', 'oem', 'OEM cabin/pollen filter'),
    ('40000000-0000-0000-0000-000000000007', 'NGK-BKR6E', 'NGK', 'Spark plug', 'ignition', 'aftermarket', 'Standard nickel spark plug, sold individually');

INSERT INTO part_fitments (id, part_id, vehicle_id, year_from, year_to, notes) VALUES
    ('41000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 2003, 2008, NULL),
    ('41000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 2003, 2008, 'Direct aftermarket replacement'),
    ('41000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000003', 2005, 2015, NULL),
    ('41000000-0000-0000-0000-000000000004', '40000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000001', 2003, 2008, NULL),
    ('41000000-0000-0000-0000-000000000005', '40000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000002', 2009, 2013, NULL),
    ('41000000-0000-0000-0000-000000000006', '40000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000001', 2003, 2008, 'Cross-reference for OEM filter'),
    ('41000000-0000-0000-0000-000000000007', '40000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000003', 2005, 2015, NULL),
    ('41000000-0000-0000-0000-000000000008', '40000000-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000003', 2005, 2015, NULL),
    ('41000000-0000-0000-0000-000000000009', '40000000-0000-0000-0000-000000000006', '20000000-0000-0000-0000-000000000005', 2007, 2011, NULL),
    ('41000000-0000-0000-0000-000000000010', '40000000-0000-0000-0000-000000000007', '20000000-0000-0000-0000-000000000004', 2000, 2006, NULL),
    ('41000000-0000-0000-0000-000000000011', '40000000-0000-0000-0000-000000000007', '20000000-0000-0000-0000-000000000005', 2007, 2011, NULL);

INSERT INTO part_alternatives (id, part_id, alternative_part_id) VALUES
    ('42000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000002'),
    ('42000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000004');

INSERT INTO supplier_parts (id, supplier_id, part_id, price, currency_code, stock, lead_time_days) VALUES
    ('50000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', 480.00, 'NLE', 6, 0),
    ('50000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000001', 510.00, 'NLE', 2, 1),
    ('50000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000001', 495.00, 'NLE', 0, 10),
    ('50000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000002', 310.00, 'NLE', 14, 0),
    ('50000000-0000-0000-0000-000000000005', '30000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000003', 85.00, 'NLE', 30, 0),
    ('50000000-0000-0000-0000-000000000006', '30000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000004', 60.00, 'NLE', 25, 0),
    ('50000000-0000-0000-0000-000000000007', '30000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000005', 1200.00, 'NLE', 0, 21),
    ('50000000-0000-0000-0000-000000000008', '30000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000006', 120.00, 'NLE', 8, 0),
    ('50000000-0000-0000-0000-000000000009', '30000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000007', 4.50, 'USD', 100, 0);

INSERT INTO listings (id, seller_id, vehicle_id, vin, price, currency_code, condition, mileage_km, description, status) VALUES
    ('60000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'JTDBR32E173000001', 95000.00, 'NLE', 'used', 168000, 'Well maintained, single owner, new tyres.', 'active'),
    ('60000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000003', 'MR0KZN15805000002', 210000.00, 'NLE', 'used', 240000, 'Strong workhorse, minor bodywork needed.', 'active'),
    ('60000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000005', 'JHLRE4H8711000003', 260000.00, 'NLE', 'used', 132000, 'Imported, AC and 4WD fully functional.', 'reserved'),
    ('60000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000004', 'JN1BN15A120000004', 55000.00, 'NLE', 'used', 210000, 'Sold as-is, needs clutch work.', 'draft');

INSERT INTO listing_photos (id, listing_id, url, position) VALUES
    ('61000000-0000-0000-0000-000000000001', '60000000-0000-0000-0000-000000000001', 'https://cdn.saloneparts.sl/listings/1/front.jpg', 0),
    ('61000000-0000-0000-0000-000000000002', '60000000-0000-0000-0000-000000000001', 'https://cdn.saloneparts.sl/listings/1/interior.jpg', 1),
    ('61000000-0000-0000-0000-000000000003', '60000000-0000-0000-0000-000000000002', 'https://cdn.saloneparts.sl/listings/2/front.jpg', 0),
    ('61000000-0000-0000-0000-000000000004', '60000000-0000-0000-0000-000000000003', 'https://cdn.saloneparts.sl/listings/3/front.jpg', 0);

INSERT INTO orders (id, buyer_id, status, payment_method, payment_status, delivery_address, total_amount, currency_code, created_at) VALUES
    ('70000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000003', 'completed', 'mobile_money', 'paid', 'Congo Cross, Freetown', 480.00, 'NLE', now() - interval '5 days');

INSERT INTO order_items (id, order_id, item_type, supplier_part_id, quantity, unit_price, currency_code, estimated_delivery, fulfillment_status) VALUES
    ('71000000-0000-0000-0000-000000000001', '70000000-0000-0000-0000-000000000001', 'part', '50000000-0000-0000-0000-000000000001', 1, 480.00, 'NLE', now() - interval '4 days', 'delivered');

INSERT INTO orders (id, buyer_id, status, payment_method, payment_status, delivery_address, total_amount, currency_code, created_at) VALUES
    ('70000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000004', 'confirmed', 'bank_transfer', 'paid', 'Bo Town, Bo', 395.00, 'NLE', now() - interval '1 day');

INSERT INTO order_items (id, order_id, item_type, supplier_part_id, quantity, unit_price, currency_code, estimated_delivery, fulfillment_status) VALUES
    ('71000000-0000-0000-0000-000000000002', '70000000-0000-0000-0000-000000000002', 'part', '50000000-0000-0000-0000-000000000004', 1, 310.00, 'NLE', now() + interval '2 days', 'ordered_from_supplier'),
    ('71000000-0000-0000-0000-000000000003', '70000000-0000-0000-0000-000000000002', 'part', '50000000-0000-0000-0000-000000000005', 1, 85.00, 'NLE', now() + interval '2 days', 'ordered_from_supplier');

INSERT INTO orders (id, buyer_id, status, payment_method, payment_status, delivery_address, total_amount, currency_code, created_at) VALUES
    ('70000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000003', 'pending', 'bank_transfer', 'unpaid', 'Aberdeen, Freetown', 260000.00, 'NLE', now() - interval '2 hours');

INSERT INTO order_items (id, order_id, item_type, listing_id, quantity, unit_price, currency_code, fulfillment_status) VALUES
    ('71000000-0000-0000-0000-000000000004', '70000000-0000-0000-0000-000000000003', 'listing', '60000000-0000-0000-0000-000000000003', 1, 260000.00, 'NLE', 'pending');

COMMIT;
