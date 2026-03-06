# Backend Port Notes

This package ports the backend logic into the latest `frontend-producer_view` branch structure.

## Added JSON endpoints
- `GET /api/products/`
- `POST /api/products/`
- `GET /api/products/<id>/`
- `PUT /api/products/<id>/`
- `PATCH /api/products/<id>/`
- `DELETE /api/products/<id>/`

- `GET /api/producers/`
- `GET /api/producers/<id>/`

## Existing page routes kept intact
- `/products/`
- `/products/add/`
- `/producer/dashboard/`
- `/customer/dashboard/`

## Important limitation
This branch does **not** have marketplace-style models like Order, Inventory, Payment, or Category.
So those endpoints were not ported, because they would not line up with the current schema.
