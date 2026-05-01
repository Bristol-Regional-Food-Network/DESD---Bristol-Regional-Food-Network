# New Features – Recurring Orders & Network Commission Reports

This document describes two features added to the Bristol Regional Food Network
platform on top of the existing Django interface. **No existing templates were
reskinned** – both features reuse the project's current Bootstrap 5 layout, the
shared `base/base.html`, and the existing manager `nav-tabs` pattern.

---

## TC-018 – Recurring Orders for Restaurants

**User story:** *As a restaurant owner I want to establish regular weekly
orders so that I can simplify sourcing local ingredients.*

### What it does
- Restaurants (any account with the `customer` role) can turn any normal
  basket checkout into a **recurring order template** by ticking *"Make this a
  recurring order"* on the existing checkout page.
- Recurrence supports **Every week** or **Every two weeks**, with separate
  fields for **Order Day** (when the order is generated) and **Delivery Day**
  (when the producer delivers).
- A new **Recurring Orders** management area lets the restaurant:
  - View all recurring templates with next scheduled order/delivery date.
  - Drill into a template to see items grouped by producer.
  - **Modify the next scheduled order only** – per-line `next_quantity_override`
    keeps the template untouched.
  - Or, alternatively, **modify the template permanently** so all future
    orders use the new quantities.
  - **Pause / Resume / Cancel** the recurring order at any time.
- Producers see each generated order in their existing producer dashboard, so
  they receive advance notice every time a new instance is generated.
- The list page surfaces **unavailable products** in any active template so the
  restaurant can swap them out before the next run.

### Where to find it
- Top-nav button **"Recurring Orders"** (visible to logged-in customer
  accounts).
- Checkout: a new *"Make this a recurring order"* section, hidden until the
  checkbox is ticked.
- After a successful payment, the order confirmation page links straight to
  the new recurring template (when one was created).

### URLs
| Path | Purpose |
|------|---------|
| `/basket/recurring/` | List of the user's recurring templates |
| `/basket/recurring/<id>/` | Detail / management for a single template |
| `/basket/recurring/<id>/modify/` | Modify next scheduled order or whole template |
| `/basket/recurring/<id>/pause/` | Pause or resume (POST) |
| `/basket/recurring/<id>/cancel/` | Cancel permanently (POST) |

### New code
- `basket/models.py` — added `RecurringOrder` and `RecurringOrderItem` models.
- `basket/views.py` — five new views (`recurring_orders_list`,
  `recurring_order_detail`, `recurring_order_modify_next`,
  `recurring_order_pause`, `recurring_order_cancel`) plus a small piece in the
  existing `checkout` view that creates the template post-payment.
- `basket/urls.py` — route table extended.
- `basket/admin.py` — Django admin registration with inline items.
- `basket/migrations/0006_recurring_orders.py` — schema migration.
- New templates:
  - `basket/templates/basket/recurring_orders_list.html`
  - `basket/templates/basket/recurring_order_detail.html`
  - `basket/templates/basket/recurring_order_modify.html`
- Edited templates:
  - `basket/templates/basket/checkout.html` (adds the recurring-order section)
  - `basket/templates/basket/payment_success.html` (links to the new template)
  - `templates/base/base.html` (top-nav link for customers)

### Acceptance criteria coverage
- ✅ Recurring template maintains product selections and quantities.
- ✅ Recurrence (weekly / fortnightly) and delivery day are configurable.
- ✅ Individual instances editable without affecting the template
  (`next_quantity_override`).
- ✅ Payment snapshot stored on each template (cardholder + last 4 + address).
- ✅ Pause / resume / cancel flows.
- ✅ Unavailable products surface as warnings on the list and detail pages.

---

## TC-025 – Network Commission / Financial Reports

**User story:** *As a system administrator I want to monitor the network
commission calculations so that I can ensure financial accuracy and generate
reports.*

### What it does
This feature was previously implemented in the codebase but **had no entry
point in the website interface**. The new work:

1. Adds a **"Financial Reports"** tab inside the existing manager nav-tabs
   (Orders / Customers / Producers / **Financial Reports**) so it is reachable
   from every manager page.
2. Adds a matching **Financial Reports card** to the manager dashboard.
3. Reskins the report page to use the same Bootstrap card / `nav-tabs` /
   `table table-striped` pattern as the rest of the manager UI – no project-
   wide template changes.

### What the report shows
- Filterable by **date range, producer, status**.
- Period summary cards: orders processed, total order value, network
  commission (5%), producer payout (95%).
- Detailed per-order audit table with subtotal, commission, producer total,
  order total, and a drill-down link.
- **Per-order detail page** showing the commission calculation step-by-step
  and a per-producer payout breakdown (so a multi-vendor order's 95% is
  fairly distributed among the producers in it).
- **Monthly summary** – last 6 months at a glance.
- **Year-to-date totals**.
- **CSV export** with the same filters and a totals footer (suitable for
  accounting software).
- All currency values rounded **half-up to 2 decimals** for accounting
  compliance.

### Where to find it
- Manager Dashboard → **Financial Reports** card or top nav-tab.
- Direct URL: `/manager/financial-reports/`.

### URLs
| Path | Purpose |
|------|---------|
| `/manager/financial-reports/` | Filterable report + CSV export (`?export=csv`) |
| `/manager/financial-reports/<order_id>/` | Per-order audit drill-down |

### New code
- `managers/views.py` — added `financial_reports` and
  `financial_report_detail` views plus helpers for date parsing, dataset
  building, monthly summaries, and YTD totals.
- `managers/urls.py` — two new routes.
- New templates:
  - `templates/managers/financial_reports.html`
  - `templates/managers/financial_report_detail.html`
- Edited templates (added the Financial Reports tab only):
  - `templates/managers/dashboard.html`
  - `templates/managers/orders_list.html`
  - `templates/managers/customers_list.html`
  - `templates/managers/producers_list.html`

### Acceptance criteria coverage
- ✅ 5% commission and 95% producer split applied consistently.
- ✅ Multi-vendor payouts computed from each producer's own subtotal.
- ✅ CSV export for accounting tools.
- ✅ Filters by date range, producer, and status.
- ✅ Per-order audit trail traceable back to the source `Order`.
- ✅ Monthly + YTD summaries.
- ✅ Half-up rounding to 2 decimals on every monetary calculation.
- ✅ Manager-only access enforced via the existing `userprofile.role` check
  (other roles get a `PermissionDenied`).

---

## Database migration

Both features add a single migration file:

```
basket/migrations/0006_recurring_orders.py
```

Apply it with:

```bash
python manage.py migrate basket
```

(TC-025 reports run on existing `Order` / `ProducerOrder` data and need no
schema changes.)
