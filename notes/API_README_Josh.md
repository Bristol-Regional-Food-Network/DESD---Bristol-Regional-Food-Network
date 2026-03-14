# Marketplace Backend API (Sprint 1)

This branch adds a **backend-only JSON API** (no HTML/templates required) on top of the existing Marketplace database schema.
The API is implemented using Django view/controller functions + URL routing under `/api/`.

---

## Run (Docker)

From the repo root (where `docker-compose.yml` is):

```bash
docker compose up --build
```

API base URL:
- `http://localhost:8000/api/`

---

## Quick Demo Checklist (2–3 minutes)

1. **Health**
   - `GET /api/health/`

2. **Create or confirm seed data**
   - You need at least **one Producer** and **one Category** in the database before creating products.
   - Easiest approach for Sprint 1: create them via Django admin.

3. **Product CRUD**
   - `POST /api/products/`
   - `GET /api/products/`
   - `PATCH /api/products/<id>/`
   - `DELETE /api/products/<id>/`

4. **Inventory update**
   - `PUT /api/products/<id>/inventory/`

5. *(Optional)* **Order creation**
   - `POST /api/orders/` (decrements stock)

---

## Endpoints

### Health

#### `GET /api/health/`
**Purpose:** confirms the API is running.

**Response:**
```json
{ "status": "ok" }
```

---

### Producers

#### `GET /api/producers/`
**Purpose:** list all producers.

**Typical use:** used by the frontend to display producer info and to locate valid `producer_id` values for product creation.

---

### Categories

#### `GET /api/categories/`
**Purpose:** list all categories.

**Typical use:** used by the frontend to populate category filters / dropdowns and to locate valid `category_id` values.

---

### Products

#### `GET /api/products/`
**Purpose:** list products.

**Query params (optional):**
- `producer_id` (int) — filter to a producer
- `category_id` (int) — filter to a category
- `active` (`true`/`false`) — filter by active flag

**Examples:**
- `/api/products/?producer_id=1`
- `/api/products/?category_id=2`
- `/api/products/?active=true`

---

#### `POST /api/products/`
**Purpose:** create a new product.

**JSON body (example):**
```json
{
  "name": "Apples",
  "description": "Fresh apples",
  "unit": "kg",
  "producer_id": 1,
  "category_id": 2,
  "price": "2.50",
  "is_active": true,
  "inventory": { "stock_qty": 20 }
}
```

**Notes:**
- `producer_id` and `category_id` must already exist.
- `price` must be > 0.
- `inventory` is optional. If provided, inventory is created/updated for the product.

---

#### `GET /api/products/<id>/`
**Purpose:** fetch a single product by ID.

---

#### `PUT /api/products/<id>/`
**Purpose:** full update of a product.

Use `PUT` when sending a complete object.

---

#### `PATCH /api/products/<id>/`
**Purpose:** partial update of a product.

Use `PATCH` when editing only a few fields (recommended).

---

#### `DELETE /api/products/<id>/`
**Purpose:** delete a product.

---

### Inventory (per product)

#### `GET /api/products/<product_id>/inventory/`
**Purpose:** return inventory for the given product.

If inventory does not exist yet, it will be created with defaults when you update it.

---

#### `PUT /api/products/<product_id>/inventory/`
#### `PATCH /api/products/<product_id>/inventory/`
**Purpose:** update stock and availability dates.

**Example JSON body:**
```json
{
  "stock_qty": 15,
  "available_from": "2026-03-01",
  "available_to": "2026-03-31"
}
```

---

### Customers

#### `GET /api/customers/`
**Purpose:** list customers.

**Query params (optional):**
- `active` (`true`/`false`)
- `email`
- `postcode`

---

#### `POST /api/customers/`
**Purpose:** create a new customer.

**Example JSON body:**
```json
{
  "full_name": "Josh James",
  "email": "josh@example.com",
  "phone": "07123456789",
  "postcode": "BS1 1AA",
  "is_active": true
}
```

---

#### `GET /api/customers/<id>/`
**Purpose:** fetch customer by ID.

#### `PUT/PATCH /api/customers/<id>/`
**Purpose:** update customer details.

#### `DELETE /api/customers/<id>/`
**Purpose:** delete customer.

---

### Orders

#### `GET /api/orders/`
**Purpose:** list orders.

**Query params (optional):**
- `customer_id` (int)
- `status` (string)

---

#### `POST /api/orders/`
**Purpose:** create an order with items and decrement stock.

**Example JSON body:**
```json
{
  "customer_id": 1,
  "fulfilment_method": "collection",
  "delivery_notes": "",
  "items": [
    { "product_id": 10, "quantity": 2 },
    { "product_id": 12, "quantity": 1 }
  ]
}
```

**Behaviour:**
- Creates the order + `OrderItem` rows
- Locks product/inventory rows (`select_for_update`) to avoid overselling
- Decrements inventory stock
- Recalculates order totals

**Errors:**
- Returns `409` if insufficient stock.

---

#### `GET /api/orders/<id>/`
**Purpose:** fetch a single order (includes items + payment where available).

---

#### `PUT/PATCH /api/orders/<id>/`
**Purpose:** update order status.

**Example JSON body:**
```json
{ "status": "cancelled" }
```

**Behaviour:**
- If changing to `cancelled`, stock is restocked for all items.

---

#### `DELETE /api/orders/<id>/`
**Purpose:** deletes an order (mainly for testing/admin).  
**Behaviour:** restocks items then deletes the order.

---

### Payments (simple test payment)

#### `GET /api/orders/<id>/payment/`
**Purpose:** fetch payment info for the order.

---

#### `POST/PUT/PATCH /api/orders/<id>/payment/`
**Purpose:** create/update a payment record.

**Example JSON body:**
```json
{
  "provider": "test",
  "provider_ref": "demo-123",
  "amount_paid": "12.50",
  "currency": "GBP",
  "status": "paid"
}
```

**Behaviour:**
- Creates or updates a `Payment` row
- If status is `paid` and the order is still `pending`, the order is marked as `paid`

---

## Notes / Limitations (Sprint 1)
- Authentication/authorisation for API endpoints is not enforced yet (focus is core backend logic + routing).
- Producers/Categories should be created in admin for demo purposes.
- Payment is a simple test endpoint, not a real provider integration.
