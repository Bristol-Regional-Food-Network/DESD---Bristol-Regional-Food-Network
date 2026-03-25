# Admin — Quick Overview

I added a small, separate management UI so you can view and manage orders, customers and producers without leaving the site.

What I changed (high level)
- Added a basic `Order` model to `basket/models.py` to record completed checkouts.
- Added lightweight management views in `core/admin_views.py` and routes in `core/urls.py` under `/management/`.
- Added templates in `templates/admin/` for a small management UI and a shared top navigation (`management_nav.html`).
- Modified checkout (`basket/views.py`) so an authenticated user creates an `Order` record when paying.

Where to look in the code
- Order model: `basket/models.py`
- Views and URLs: `core/admin_views.py`, `core/urls.py`
- Templates: `templates/admin/` (dashboard, orders, customers, producers, forms)
- Checkout change: `basket/views.py`

How to use it locally
1. Make sure migrations are applied:

```bash
python manage.py makemigrations
python manage.py migrate
```

2. Start the dev server:

```bash
python manage.py runserver
```

3. Visit the pages:
- Lightweight management UI: `/management/`
- Orders list: `/management/orders/`
- Customers: `/management/customers/`
- Producers: `/management/producers/`
- Django admin (unchanged): `/admin/`
<<<<<<< HEAD
=======


>>>>>>> cb9dc9a (Include README and migration for admin role)
