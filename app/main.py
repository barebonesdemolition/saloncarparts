from uuid import UUID
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.ai_assistant import router as ai_router
from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.services.listings import list_active_listings
from app.services.listings_sell import create_vehicle_listing
from app.services.orders import (
    confirm_order_payment,
    create_part_order,
    get_part_order,
    update_fulfillment_status,
)
from app.services.parts_finder import find_recommendations
from app.services.vin_lookup import VinLookupError, decode_vin, lookup_vin
from app.services.vin_parts import find_parts_by_vin
from app.services.vin_suggestions import suggest_vehicles_by_vin
from app.services.vehicles import list_vehicle_catalog

app = FastAPI(
    title="AutoParts & VIN Finder API",
    description="E-commerce catalog with integrated rule-based AI mechanic assistant",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=Path(__file__).with_name("static")), name="static")
templates = Jinja2Templates(directory=Path(__file__).with_name("templates"))
app.include_router(ai_router)


class PartOrderPayload(BaseModel):
    buyer_id: str = Field(..., min_length=1)
    supplier_part_id: str = Field(..., min_length=1)
    quantity: int = Field(default=1, ge=1)
    payment_method: str = Field(default="mobile_money")
    delivery_address: str = Field(default="")


class PaymentConfirmationPayload(BaseModel):
    payment_reference: str = Field(..., min_length=1, max_length=120)


class FulfillmentUpdatePayload(BaseModel):
    fulfillment_status: str = Field(..., min_length=1)


class VehicleListingPayload(BaseModel):
    seller_id: str = Field(..., min_length=1)
    make: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    year: int = Field(..., ge=1900, le=2100)
    price: str = Field(..., min_length=1)
    currency_code: str = Field(default="NLE", min_length=3, max_length=3)
    condition: str = Field(default="used")
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    mileage_km: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=2000)
    photo_url: str | None = Field(default=None, max_length=2000)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("vin_lookup.html", {"request": request})
    """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Salon AutoZone Finder</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 2rem; background: #f5f7fb; color: #1f2937; }
                .panel { max-width: 1100px; margin: auto; background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
                .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
                input, button { padding: 0.8rem; border-radius: 8px; border: 1px solid #d1d5db; font-size: 1rem; }
                button { background: #0f766e; color: white; border: none; cursor: pointer; }
                .result { margin-top: 1.5rem; border-top: 1px solid #e5e7eb; padding-top: 1rem; }
                .suggestions { margin-top: -0.5rem; }
                .suggestion { background: white; border: 1px solid #d1d5db; padding: 0.65rem; cursor: pointer; }
                .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem; margin-top: 0.75rem; }
                .report { margin-top: 1rem; padding: 1rem; border-left: 4px solid #0f766e; background: #f8fafc; }
                .report-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
                .check { padding: 0.55rem 0; border-bottom: 1px solid #e5e7eb; }
                .pass { color: #047857; font-weight: bold; }
                .flag { color: #b45309; font-weight: bold; }
                details { margin-top: 0.6rem; padding: 0.7rem; background: white; border: 1px solid #e5e7eb; }
                .chart { width: 100%; height: 130px; background: white; border: 1px solid #e5e7eb; }
                .listing-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-top: 1.5rem; }
                img { max-width: 100%; border-radius: 8px; height: 150px; object-fit: cover; display: block; }
            </style>
        </head>
        <body>
            <div class="panel">
                <h1>Salon AutoZone Marketplace</h1>
                <p>Use a VIN or enter the vehicle manually if the VIN is unavailable.</p>

                <div class="grid">
                    <input id="vin" type="text" placeholder="VIN (17 chars)" autocomplete="off" />
                    <select id="make"><option value="">Select make</option></select>
                    <select id="model"><option value="">Select model</option></select>
                    <select id="year"><option value="">Select year</option></select>
                    <button onclick="searchParts()">Find compatible parts</button>
                </div>
                <div id="vin-suggestions" class="suggestions"></div>

                <div id="results" class="result"></div>
                <div class="grid">
                    <input id="buyer-id" type="text" placeholder="Buyer ID to order" />
                    <input id="delivery-address" type="text" placeholder="Delivery address" />
                    <select id="payment-method">
                        <option value="mobile_money">Mobile money</option>
                        <option value="cash">Cash</option>
                        <option value="bank_transfer">Bank transfer</option>
                        <option value="card">Card</option>
                    </select>
                </div>
                <div class="grid">
                    <input id="order-id" type="text" placeholder="Order ID to track" />
                    <button type="button" onclick="trackOrder()">Track order</button>
                    <input id="payment-reference" type="text" placeholder="Payment reference" />
                    <button type="button" onclick="confirmPayment()">Confirm payment</button>
                    <select id="fulfillment-status">
                        <option value="pending">Pending</option>
                        <option value="ordered_from_supplier">Ordered from supplier</option>
                        <option value="shipped">Shipped</option>
                        <option value="delivered">Delivered</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                    <button type="button" onclick="updateFulfillment()">Update fulfillment</button>
                </div>
                <div id="order-status" class="result" aria-live="polite"></div>

                <h2>Example vehicles</h2>
                <div class="listing-grid example-grid">
                    <div class="card">
                        <img src="https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=900&q=80" alt="Toyota Corolla example vehicle" />
                        <strong>Toyota Corolla</strong><br />
                        Common sedan parts and service fitments
                    </div>
                    <div class="card">
                        <img src="https://images.unsplash.com/photo-1559416523-140ddc3d238c?auto=format&fit=crop&w=900&q=80" alt="Toyota Hilux example vehicle" />
                            <input name="seller_id" id="seller-id" type="text" placeholder="Seller ID" required />
                        Popular pickup parts and maintenance items
                    </div>
                        <button type="button" onclick="forgetUserInfo()">Forget saved information</button>
                    <div class="card">
                        <img src="https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=900&q=80" alt="Honda CR-V example vehicle" />
                        <strong>Honda CR-V</strong><br />
                        SUV fitments for everyday workshop jobs
                    </div>
                </div>

                <h2>Active vehicle listings</h2>
                <div id="listings" class="listing-grid"></div>

                <h2>Sell a vehicle</h2>
                <form id="sell-form" class="grid">
                    <input name="seller_id" type="text" placeholder="Seller ID" required />
                    <select name="sell-make" id="sell-make" required>
                        <option value="">Select make</option>
                    </select>
                    <select name="sell-model" id="sell-model" required>
                        <option value="">Select model</option>
                    </select>
                    <input name="sell-year" type="number" min="1900" max="2100" placeholder="Year" required />
                    <input name="price" type="number" min="0" step="0.01" placeholder="Price (NLE)" required />
                    <select name="condition">
                        <option value="used">Used</option>
                        <option value="new">New</option>
                        <option value="salvage">Salvage</option>
                    </select>
                    <input name="vin" type="text" minlength="17" maxlength="17" placeholder="VIN (optional)" />
                    <input name="mileage_km" type="number" min="0" placeholder="Mileage (km)" />
                    <input name="description" type="text" maxlength="2000" placeholder="Description" />
                    <input name="photo_url" type="url" maxlength="2000" placeholder="Vehicle photo URL (optional)" />
                    <button type="submit">Publish listing</button>
                </form>
                <div id="sell-status" class="result" aria-live="polite"></div>
            </div>

            <script>
                async function searchParts() {
                    const vin = document.getElementById('vin').value.trim();
                    const make = document.getElementById('make').value.trim();
                    const model = document.getElementById('model').value.trim();
                    const year = document.getElementById('year').value.trim();
                        rememberUserInfo();

                    const params = new URLSearchParams();
                    if (vin) params.set('vin', vin);
                    if (make) params.set('make', make);
                    if (model) params.set('model', model);
                    if (year) params.set('year', year);

                    const url = '/api/parts-finder?' + params.toString();
                    const lookup = vin ? await fetch('/api/vin-lookup?vin=' + encodeURIComponent(vin)) : null;
                    const response = await fetch(url);
                    const data = await response.json();

                    const results = document.getElementById('results');
                    if (lookup) {
                        const report = await lookup.json();
                        if (lookup.ok) {
                            results.innerHTML = renderInspectionReport(report);
                        } else {
                            results.innerHTML = `<div class="card">VIN lookup: ${report.detail || 'unavailable'}</div>`;
                        }
                    }
                    if (!Array.isArray(data) || data.length === 0) {
                        results.innerHTML += '<p>No compatible parts found.</p>';
                        return;
                    }

                    results.innerHTML += data.map(item => `
                        <div class="card">
                            <strong>${item.name}</strong><br />
                            Brand: ${item.brand || '—'}<br />
                            Category: ${item.category || '—'}<br />
                            Supplier: ${item.supplier_name || '—'}<br />
                            Price: ${item.price || '—'} ${item.currency_code || ''}<br />
                            Stock: ${item.stock ?? '—'}<br />
                            Lead time: ${item.lead_time_days ?? '—'} days<br />
                            Availability: ${item.availability_status || '—'}
                            <br /><button type="button" onclick="orderPart('${item.supplier_part_id}', '${item.name.replace(/'/g, "\\'")}')">Order this part</button>
                        </div>
                    `).join('');
                }

                let vinSuggestionTimer;
                document.getElementById('vin').addEventListener('input', (event) => {
                    clearTimeout(vinSuggestionTimer);
                    const vin = event.target.value.trim();
                    const suggestions = document.getElementById('vin-suggestions');
                    if (vin.length < 3) {
                        suggestions.innerHTML = '';
                        return;
                    }
                    vinSuggestionTimer = setTimeout(async () => {
                        const response = await fetch('/api/vin-suggestions?vin=' + encodeURIComponent(vin));
                        if (!response.ok) return;
                        const data = await response.json();
                        suggestions.innerHTML = data.map((item) => `<div class="suggestion" data-prefix="${item.matched_prefix}"><strong>${item.make} ${item.model}</strong> (${item.year_from}-${item.year_to})<br /><small>Alpha confidence: ${Math.round(item.confidence * 100)}%</small></div>`).join('');
                        suggestions.querySelectorAll('.suggestion').forEach((suggestion) => {
                            suggestion.addEventListener('click', () => {
                                document.getElementById('vin').value = suggestion.dataset.prefix;
                                suggestions.innerHTML = '';
                            });
                        });
                    }, 180);
                });

                async function orderPart(supplierPartId, partName) {
                    const buyerId = document.getElementById('buyer-id').value.trim();
                    const deliveryAddress = document.getElementById('delivery-address').value.trim();
                    const paymentMethod = document.getElementById('payment-method').value;
                    const results = document.getElementById('results');
                    if (!buyerId || !deliveryAddress) {
                        results.insertAdjacentHTML('afterbegin', '<div class="card">Enter a buyer ID and delivery address before ordering.</div>');
                        return;
                    }
                    const response = await fetch('/api/orders/parts', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            buyer_id: buyerId,
                            supplier_part_id: supplierPartId,
                            quantity: 1,
                            payment_method: paymentMethod,
                            delivery_address: deliveryAddress
                        })
                    });
                    const data = await response.json();
                    results.insertAdjacentHTML('afterbegin', `<div class="card">${response.ok ? `Order placed for ${partName}. Order ID: ${data.order_id}` : (data.detail || 'Unable to place order.')}</div>`);
                    if (response.ok) {
                        document.getElementById('order-id').value = data.order_id;
                        trackOrder();
                    }
                }

                async function trackOrder() {
                    const orderId = document.getElementById('order-id').value.trim();
                    const status = document.getElementById('order-status');
                    if (!orderId) {
                        status.textContent = 'Enter an order ID to track.';
                        return;
                    }
                    const response = await fetch('/api/orders/' + encodeURIComponent(orderId));
                    const data = await response.json();
                    if (!response.ok) {
                        status.textContent = data.detail || 'Order could not be found.';
                        return;
                    }
                    status.innerHTML = `<div class="card"><strong>Order ${data.order_id}</strong><br />Order status: ${data.status}<br />Payment: ${data.payment_status}<br />Fulfillment: ${data.item.fulfillment_status}<br />Total: ${data.total_amount} ${data.currency_code}</div>`;
                }

                async function confirmPayment() {
                    const orderId = document.getElementById('order-id').value.trim();
                    const reference = document.getElementById('payment-reference').value.trim();
                    const status = document.getElementById('order-status');
                    if (!orderId || !reference) {
                        status.textContent = 'Enter an order ID and payment reference.';
                        return;
                    }
                    const response = await fetch('/api/orders/' + encodeURIComponent(orderId) + '/confirm-payment', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({payment_reference: reference})
                    });
                    const data = await response.json();
                    status.textContent = response.ok ? `Payment confirmed for order ${data.order_id}.` : (data.detail || 'Payment could not be confirmed.');
                    if (response.ok) trackOrder();
                }

                async function updateFulfillment() {
                    const orderId = document.getElementById('order-id').value.trim();
                    const fulfillmentStatus = document.getElementById('fulfillment-status').value;
                    const status = document.getElementById('order-status');
                    if (!orderId) {
                        status.textContent = 'Enter an order ID before updating fulfillment.';
                        return;
                    }
                    const response = await fetch('/api/orders/' + encodeURIComponent(orderId) + '/fulfillment', {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({fulfillment_status: fulfillmentStatus})
                    });
                    const data = await response.json();
                    status.textContent = response.ok ? `Fulfillment updated to ${data.fulfillment_status}.` : (data.detail || 'Fulfillment could not be updated.');
                    if (response.ok) trackOrder();
                }

                function renderInspectionReport(report) {
                    const vehicle = report.vehicle || {};
                    const checklist = [
                        ['VIN decode', Boolean(vehicle.make && vehicle.model)],
                        ['Manufacturer identified', Boolean(vehicle.make)],
                        ['Model year identified', Boolean(vehicle.model_year)],
                        ['Powertrain data', Boolean(vehicle.engine || vehicle.fuel_type)],
                        ['Body classification', Boolean(vehicle.body_class)],
                        ['Plant country', Boolean(vehicle.plant_country)],
                        ['Recall docket checked', true]
                    ];
                    const checks = checklist.map(([label, passed]) => `<div class="check"><span class="${passed ? 'pass' : 'flag'}">${passed ? 'PASS' : 'FLAG'}</span> ${label}</div>`).join('');
                    const recalls = report.recalls.length
                        ? report.recalls.map((recall) => `<details><summary>${recall.Component || 'Recall record'}</summary><p>${recall.Summary || 'No summary supplied.'}</p><p><strong>Consequence:</strong> ${recall.Conequence || recall.Consequence || 'See manufacturer notice.'}</p><p><strong>Remedy:</strong> ${recall.Remedy || 'Contact an authorized repairer.'}</p></details>`).join('')
                        : '<p>No recall records returned by NHTSA for this VIN.</p>';
                    const points = mileageTrend(report.vin);
                    return `<div class="report">
                        <h3>${vehicle.make || 'Unknown'} ${vehicle.model || 'vehicle'} ${vehicle.model_year || ''}</h3>
                        <p><strong>VIN:</strong> ${report.vin} | Source: ${report.source}</p>
                        <div class="report-grid">
                            <div><h4>Inspection checklist</h4>${checks}</div>
                            <div><h4>Specifications</h4><p>Trim: ${vehicle.trim || '—'}</p><p>Body: ${vehicle.body_class || '—'}</p><p>Engine: ${vehicle.engine || '—'}</p><p>Fuel: ${vehicle.fuel_type || '—'}</p><p>Plant: ${vehicle.plant_country || '—'}</p></div>
                            <div><h4>Mileage trend</h4><svg class="chart" viewBox="0 0 320 130" role="img" aria-label="Estimated mileage trend"><polyline fill="none" stroke="#0f766e" stroke-width="3" points="${points}" /><line x1="10" y1="112" x2="310" y2="112" stroke="#cbd5e1" /></svg><small>Illustrative estimate for demo use, not an odometer record.</small></div>
                        </div>
                        <h4>Recall docket (${report.recalls.length})</h4>${recalls}
                    </div>`;
                }

                function mileageTrend(vin) {
                    let seed = 0;
                    for (const character of vin) seed = (seed * 31 + character.charCodeAt(0)) % 1000;
                    return [0, 1, 2, 3, 4].map((index) => `${10 + index * 75},${108 - ((seed + index * 17) % 60)}`).join(' ');
                }

                async function loadListings() {
                    const response = await fetch('/api/listings');
                    const data = await response.json();
                    const listings = document.getElementById('listings');
                    listings.innerHTML = data.map(item => `
                        <div class="card">
                            ${item.photo_url ? `<img src="${item.photo_url}" alt="${item.make} ${item.model}" />` : ''}
                            <strong>${item.make} ${item.model}</strong><br />
                            Condition: ${item.condition || '—'}<br />
                            Mileage: ${item.mileage_km ? item.mileage_km + ' km' : '—'}<br />
                            Price: ${item.price || '—'} ${item.currency_code || ''}<br />
                            ${item.description || ''}
                        </div>
                    `).join('');
                }

                    const rememberedFields = ['vin', 'buyer-id', 'delivery-address', 'payment-method', 'seller-id'];
                    function rememberUserInfo() {
                        rememberedFields.forEach((fieldId) => {
                            const field = document.getElementById(fieldId);
                            if (field) localStorage.setItem('salonAutoZone.' + fieldId, field.value);
                        });
                    }

                    function restoreUserInfo() {
                        rememberedFields.forEach((fieldId) => {
                            const field = document.getElementById(fieldId);
                            const saved = localStorage.getItem('salonAutoZone.' + fieldId);
                            if (field && saved) field.value = saved;
                        });
                    }

                    function forgetUserInfo() {
                        rememberedFields.forEach((fieldId) => localStorage.removeItem('salonAutoZone.' + fieldId));
                        rememberedFields.forEach((fieldId) => {
                            const field = document.getElementById(fieldId);
                            if (field) field.value = '';
                        });
                        document.getElementById('sell-status').textContent = 'Saved information cleared from this browser.';
                    }

                    rememberedFields.forEach((fieldId) => {
                        const field = document.getElementById(fieldId);
                        if (field) field.addEventListener('change', rememberUserInfo);
                    });

                async function loadVehicleCatalog() {
                    const response = await fetch('/api/vehicles');
                    if (!response.ok) return;
                    const catalog = await response.json();
                    const makeSelect = document.getElementById('sell-make');
                    const modelSelect = document.getElementById('sell-model');
                    const buyerMakeSelect = document.getElementById('make');
                    const buyerModelSelect = document.getElementById('model');
                    const buyerYearSelect = document.getElementById('year');
                    const modelsByMake = {};
                    catalog.forEach((vehicle) => {
                        (modelsByMake[vehicle.make] ||= []).push(vehicle);
                    });
                    Object.keys(modelsByMake).forEach((make) => {
                        const option = document.createElement('option');
                        option.value = make;
                        option.textContent = make;
                        makeSelect.appendChild(option);
                        buyerMakeSelect.appendChild(option.cloneNode(true));
                    });
                    makeSelect.addEventListener('change', (event) => {
                        modelSelect.innerHTML = '<option value="">Select model</option>';
                        (modelsByMake[event.target.value] || []).forEach((vehicle) => {
                            const option = document.createElement('option');
                            option.value = vehicle.model;
                            option.textContent = `${vehicle.model} (${vehicle.year_from}-${vehicle.year_to})`;
                            modelSelect.appendChild(option);
                        });
                    });
                    buyerMakeSelect.addEventListener('change', (event) => {
                        buyerModelSelect.innerHTML = '<option value="">Select model</option>';
                        buyerYearSelect.innerHTML = '<option value="">Select year</option>';
                        (modelsByMake[event.target.value] || []).forEach((vehicle) => {
                            const option = document.createElement('option');
                            option.value = vehicle.model;
                            option.textContent = vehicle.model;
                            option.dataset.yearFrom = vehicle.year_from;
                            option.dataset.yearTo = vehicle.year_to;
                            buyerModelSelect.appendChild(option);
                        });
                    });
                    buyerModelSelect.addEventListener('change', (event) => {
                        const selected = event.target.selectedOptions[0];
                        buyerYearSelect.innerHTML = '<option value="">Select year</option>';
                        if (!selected || !selected.dataset.yearFrom) return;
                        for (let year = Number(selected.dataset.yearFrom); year <= Number(selected.dataset.yearTo); year += 1) {
                            const option = document.createElement('option');
                            option.value = year;
                            option.textContent = year;
                            buyerYearSelect.appendChild(option);
                        }
                    });
                }

                document.getElementById('sell-form').addEventListener('submit', async (event) => {
                    event.preventDefault();
                    const form = new FormData(event.target);
                    const payload = {
                        seller_id: form.get('seller_id'),
                        make: form.get('sell-make'),
                        model: form.get('sell-model'),
                        year: Number(form.get('sell-year')),
                        price: form.get('price'),
                        condition: form.get('condition'),
                        vin: form.get('vin') || null,
                        mileage_km: form.get('mileage_km') ? Number(form.get('mileage_km')) : null,
                        description: form.get('description') || null,
                        photo_url: form.get('photo_url') || null
                    };

                    const response = await fetch('/api/listings/sell', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    });
                    const data = await response.json();
                    const status = document.getElementById('sell-status');
                    if (!response.ok) {
                        status.textContent = data.detail || 'Unable to publish listing.';
                        return;
                    }
                    status.textContent = `Listing ${data.listing_id} is now active.`;
                    event.target.reset();
                    loadListings();
                });

                loadListings();
                loadVehicleCatalog();
                    restoreUserInfo();
            </script>
        </body>
        </html>
        """


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "parts-finder-api"}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_email = (
        db.query(models.User).filter(models.User.email == user_data.email).first()
    )
    if existing_email is not None:
        raise HTTPException(status_code=400, detail="Email is already registered")

    existing_phone = (
        db.query(models.User).filter(models.User.phone == user_data.phone_number).first()
    )
    if existing_phone is not None:
        raise HTTPException(status_code=400, detail="Phone number is already registered")

    new_user = models.User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone_number,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": str(new_user.id)}


@app.post("/api/auth/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if user is None or not user.hashed_password or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
        },
    }


@app.get("/api/auth/me")
def get_logged_in_user(current_user: models.User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone_number": current_user.phone,
        "cars": [
            {
                "id": str(car.id),
                "user_id": str(car.user_id),
                "vin": car.vin,
                "make": car.make,
                "model": car.model,
                "year": car.year,
                "trim": car.trim,
                "engine": car.engine,
            }
            for car in current_user.cars
        ],
        "orders": [
            {
                "id": str(order.id),
                "status": order.status,
                "total_amount": order.total_amount,
                "currency_code": order.currency_code,
                "created_at": order.created_at,
                "items": [
                    {
                        "id": str(item.id),
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "currency_code": item.currency_code,
                        "fulfillment_status": item.fulfillment_status,
                    }
                    for item in order.items
                ],
            }
            for order in current_user.orders
        ],
    }


@app.get("/api/vin/decode/{vin}")
async def preview_car_from_vin(vin: str):
    try:
        return await decode_vin(vin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach VIN decoding service."
        ) from exc


@app.post(
    "/api/users/{user_id}/cars/from-vin",
    response_model=schemas.CarResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_car_by_vin(user_id: UUID, vin: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    normalized_vin = vin.strip().upper()
    existing_car = db.query(models.Car).filter(models.Car.vin == normalized_vin).first()
    if existing_car is not None:
        raise HTTPException(
            status_code=400,
            detail="A vehicle with this VIN is already registered.",
        )

    try:
        car_info = await decode_vin(normalized_vin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach VIN decoding service."
        ) from exc

    new_car = models.Car(
        user_id=user_id,
        vin=car_info["vin"],
        make=car_info["make"],
        model=car_info["model"],
        year=car_info["year"],
        trim=car_info["trim"],
        engine=(
            f"{car_info['engine_displacement']}L"
            if car_info["engine_displacement"]
            else None
        ),
    )
    db.add(new_car)
    db.commit()
    db.refresh(new_car)
    return new_car


@app.get("/api/user/dashboard/{user_id}")
def get_user_dashboard(user_id: UUID, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .options(joinedload(models.User.orders).joinedload(models.Order.items))
        .filter(models.User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found")

    vehicle_rows = db.execute(
        text(
            """
            SELECT DISTINCT
                v.id, l.vin, v.make, v.model, v.year_from, v.engine
            FROM vehicles v
            JOIN listings l ON l.vehicle_id = v.id
            WHERE l.seller_id = :user_id
               OR l.id IN (
                    SELECT oi.listing_id
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE o.buyer_id = :user_id AND oi.listing_id IS NOT NULL
               )
            ORDER BY v.make, v.model, v.year_from
            """
        ),
        {"user_id": user_id},
    ).mappings()

    item_rows = db.execute(
        text(
            """
            SELECT
                oi.id AS item_id,
                p.part_number,
                p.name AS part_name,
                l.vehicle_id
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            LEFT JOIN supplier_parts sp ON sp.id = oi.supplier_part_id
            LEFT JOIN parts p ON p.id = sp.part_id
            LEFT JOIN listings l ON l.id = oi.listing_id
            WHERE o.buyer_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings()
    items_by_id = {row["item_id"]: row for row in item_rows}

    return {
        "profile": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone,
            "member_since": user.created_at,
        },
        "vehicles": [
            {
                "id": str(row["id"]),
                "vin": row["vin"],
                "make": row["make"],
                "model": row["model"],
                "year": row["year_from"],
                "trim": None,
                "engine": row["engine"],
            }
            for row in vehicle_rows
        ],
        "order_history": [
            {
                "order_id": str(order.id),
                "car_id": next(
                    (
                        str(items_by_id[item.id]["vehicle_id"])
                        for item in order.items
                        if items_by_id[item.id]["vehicle_id"] is not None
                    ),
                    None,
                ),
                "status": order.status,
                "total_amount": order.total_amount,
                "date": order.created_at,
                "parts": [
                    {
                        "part_number": items_by_id[item.id]["part_number"],
                        "part_name": items_by_id[item.id]["part_name"],
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                    }
                    for item in order.items
                ],
            }
            for order in user.orders
        ],
    }


@app.get("/api/vin-lookup")
def vin_lookup(vin: str = Query(..., min_length=17, max_length=17)):
    try:
        return lookup_vin(vin)
    except VinLookupError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/vin/lookup/{vin}")
async def dynamic_vin_lookup(vin: str):
    cleaned_vin = vin.strip().upper()
    if len(cleaned_vin) != 17:
        raise HTTPException(status_code=400, detail="VIN must be exactly 17 characters.")

    try:
        car_data = await decode_vin(cleaned_vin)
        return {"success": True, "data": car_data}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="NHTSA lookup service unavailable.") from exc


@app.get("/api/vin-suggestions")
def vin_suggestions(vin: str = Query(..., min_length=3, max_length=17)):
    return suggest_vehicles_by_vin(vin)


@app.get("/api/parts-finder")
def parts_finder(
    vin: str | None = Query(default=None, min_length=1),
    make: str | None = Query(default=None),
    model: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=1900, le=2100),
    limit: int = Query(10, ge=1, le=20),
):
    has_vin = bool(vin and vin.strip())
    has_manual = bool(make and model and year)
    if not has_vin and not has_manual:
        raise HTTPException(status_code=400, detail="Provide a VIN or provide make, model, and year.")

    items = find_recommendations(vin=vin or "", make=make, model=model, year=year, limit=limit)
    return [
        {
            "id": item.get("part_id"),
            "name": item.get("part_name") or item.get("name"),
            "brand": item.get("brand"),
            "category": item.get("category"),
            "part_type": item.get("part_type"),
            "supplier_name": item.get("supplier_name"),
            "price": str(item.get("price")) if item.get("price") is not None else None,
            "currency_code": item.get("currency_code"),
            "stock": item.get("stock"),
            "lead_time_days": item.get("lead_time_days"),
            "availability_status": item.get("availability_status"),
            "recommendation_rank": item.get("recommendation_rank"),
        }
        for item in items
    ]


@app.get("/api/parts/by-vin/{vin}")
def parts_by_vin(vin: str):
    try:
        normalized_vin = vin.strip().upper()
        from app.services.vin_lookup import VIN_PATTERN

        if not VIN_PATTERN.fullmatch(normalized_vin):
            return JSONResponse(status_code=400, content={"error": "invalid_vin"})

        result = find_parts_by_vin(normalized_vin)
        if result is None:
            return JSONResponse(status_code=404, content={"error": "vehicle_not_found"})
        return result
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Something went wrong."},
        )


@app.get("/api/listings")
def listings(limit: int = Query(10, ge=1, le=20)):
    return list_active_listings(limit=limit)


@app.get("/api/vehicles")
def vehicles():
    return list_vehicle_catalog()


@app.post("/api/orders/parts")
def create_order(payload: PartOrderPayload):
    try:
        order = create_part_order(
            buyer_id=payload.buyer_id,
            supplier_part_id=payload.supplier_part_id,
            quantity=payload.quantity,
            payment_method=payload.payment_method,
            delivery_address=payload.delivery_address,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return order


@app.post("/api/orders/{order_id}/confirm-payment")
def confirm_payment(order_id: str, payload: PaymentConfirmationPayload):
    try:
        return confirm_order_payment(
            order_id=order_id,
            payment_reference=payload.payment_reference,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    try:
        return get_part_order(order_id=order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/orders/{order_id}/fulfillment")
def update_fulfillment(order_id: str, payload: FulfillmentUpdatePayload):
    try:
        return update_fulfillment_status(
            order_id=order_id,
            fulfillment_status=payload.fulfillment_status,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/listings/sell")
def sell_vehicle(payload: VehicleListingPayload):
    try:
        listing = create_vehicle_listing(
            seller_id=payload.seller_id,
            make=payload.make,
            model=payload.model,
            year=payload.year,
            price=payload.price,
            currency_code=payload.currency_code,
            condition=payload.condition,
            vin=payload.vin,
            mileage_km=payload.mileage_km,
            description=payload.description,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return listing
import os
import uuid
from typing import List, Optional
from enum import Enum
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Numeric, Enum as SQLEnum, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/salon_autozone")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Database Models ---
class PaymentMethod(str, Enum):
    mobile_money = "mobile_money"
    bank_transfer = "bank_transfer"
    cash = "cash"

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, default="pending")
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    payment_status = Column(String, default="unpaid")
    delivery_address = Column(String, nullable=True)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0.0)
    currency_code = Column(String(3), default="NLE")
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    item_type = Column(String, nullable=False)
    supplier_part_id = Column(UUID(as_uuid=True), nullable=True)
    listing_id = Column(UUID(as_uuid=True), nullable=True)
    quantity = Column(Numeric, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    currency_code = Column(String(3), default="NLE")

    order = relationship("Order", back_populates="items")

# --- Schemas ---
class OrderItemCreate(BaseModel):
    item_type: str
    supplier_part_id: Optional[uuid.UUID] = None
    listing_id: Optional[uuid.UUID] = None
    quantity: int = 1
    unit_price: float

class MobileMoneyCheckoutRequest(BaseModel):
    buyer_id: uuid.UUID
    phone_number: str
    provider: str  # "orange_money" or "afrimoney"
    delivery_address: Optional[str] = "Store Pickup - Freetown Hub"
    items: List[OrderItemCreate]

# --- FastAPI App ---
app = FastAPI(title="Salon AutoZone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/checkout/mobile-money")
def checkout(payload: MobileMoneyCheckoutRequest, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart items cannot be empty.")

    total = sum(item.unit_price * item.quantity for item in payload.items)

    order = Order(
        buyer_id=payload.buyer_id,
        status="confirmed",
        payment_method=PaymentMethod.mobile_money,
        payment_status="paid",
        delivery_address=payload.delivery_address,
        total_amount=total,
        currency_code="NLE"
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        db.add(OrderItem(
            order_id=order.id,
            item_type=item.item_type,
            supplier_part_id=item.supplier_part_id,
            listing_id=item.listing_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            currency_code="NLE"
        ))

    db.commit()
    return {
        "order_id": order.id,
        "status": "paid",
        "total": total,
        "currency": "NLE",
        "message": f"Payment prompt sent to {payload.phone_number} via {payload.provider.replace('_', ' ').title()}."
    }