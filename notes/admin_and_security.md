# Admin — Management UI and Security Notes

This combined document merges the lightweight admin management README with
security notes from `adham_security.md` for easy reference.

## Admin — Quick Overview

Short and simple: I added a small, separate management UI so you can view and manage orders, customers and producers without leaving the site.

### What I changed (high level)
- Added a basic `Order` model to `basket/models.py` to record completed checkouts.
- Added lightweight management views in `core/admin_views.py` and routes in `core/urls.py` under `/management/`.
- Added templates in `templates/admin/` for a small management UI and a shared top navigation (`management_nav.html`).
- Modified checkout (`basket/views.py`) so an authenticated user creates an `Order` record when paying.

### Where to look in the code
- Order model: `basket/models.py`
- Views and URLs: `core/admin_views.py`, `core/urls.py`
- Templates: `templates/admin/` (dashboard, orders, customers, producers, forms)
- Checkout change: `basket/views.py`

### How to use it locally
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

---

## Security Notes (from adham_security.md)

- I made logins safer by changing how Django keeps people logged in.
- I added settings you can change in the `.env` file.

### What you can control
- How long someone stays logged in (default 14 days).
- If closing the browser logs them out.
- If the login cookie is only sent over HTTPS (turn this on in real sites).
- If JavaScript can read the login cookie (I turned that off for safety).
- A setting to force the site to use HTTPS (use on real sites only).

### How to test locally
1. Start the app: `docker compose up -d --build`
2. Run migrations: `docker compose exec web python manage.py migrate`
3. Make a superuser: `docker compose exec web python manage.py createsuperuser`
4. Visit http://localhost:8000 and try logging in.

### Note about provided superuser
The security notes included a created superuser (for local testing):
- username : root
- password : Adham-135

---

If you want this merged file placed elsewhere or formatted differently (Markdown sections, headings, or splitting into separate docs), tell me where and how.
