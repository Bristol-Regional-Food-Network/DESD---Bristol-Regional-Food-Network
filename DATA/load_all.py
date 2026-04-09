"""
===============================================================
  Bristol Regional Food Network — Master Database Loader
===============================================================
  Run this script to populate the database with all data.

  Required files (place in same folder as this script):
    - customers_dataset.csv
    - producers_dataset.csv
    - orders_dataset.csv

  Usage:
      python load_all.py

  Make sure you have activated your virtual environment first:
      .venv\Scripts\Activate.ps1  (Windows)
      source .venv/bin/activate   (Mac/Linux)
===============================================================
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

import csv
from itertools import groupby
from django.contrib.auth.models import User
from basket.models import Order, OrderItem
from producers.models import Producer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ══════════════════════════════════════════════════════════════
#  STEP 1 — LOAD CUSTOMERS
# ══════════════════════════════════════════════════════════════

def load_customers():
    print("\n👤 Loading customers...")
    path = os.path.join(BASE_DIR, 'customers_dataset.csv')
    created = skipped = 0

    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if User.objects.filter(username=row['username']).exists():
                skipped += 1
                continue
            User.objects.create_user(
                username=row['username'],
                email=row['email'],
                password=row['password'],
                first_name=row['first_name'],
                last_name=row['last_name'],
            )
            created += 1

    print(f"   ✅ {created} customers created, {skipped} already existed")


# ══════════════════════════════════════════════════════════════
#  STEP 2 — LOAD PRODUCERS
# ══════════════════════════════════════════════════════════════

def load_producers():
    print("\n🌱 Loading producers...")
    path = os.path.join(BASE_DIR, 'producers_dataset.csv')
    created = skipped = 0

    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if User.objects.filter(username=row['username']).exists():
                skipped += 1
                continue
            user = User.objects.create_user(
                username=row['username'],
                email=row['email'],
                password=row['password'],
                first_name=row['first_name'],
                last_name=row['last_name'],
            )
            Producer.objects.create(
                user=user,
                display_name=row['display_name'],
                bio=row['bio'],
                location=row['location'],
                postcode=row['postcode'],
                phone=row['phone'],
                website=row['website'],
            )
            created += 1

    print(f"   ✅ {created} producers created, {skipped} already existed")


# ══════════════════════════════════════════════════════════════
#  STEP 3 — LOAD ORDERS
# ══════════════════════════════════════════════════════════════

def load_orders():
    print("\n🛒 Loading orders...")
    path = os.path.join(BASE_DIR, 'orders_dataset.csv')
    created_orders = created_items = skipped = 0

    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    user_map     = {u.username: u for u in User.objects.all()}
    producer_map = {p.display_name: p for p in Producer.objects.all()}

    rows.sort(key=lambda r: int(r['order_id']))

    for order_id, items in groupby(rows, key=lambda r: r['order_id']):
        items = list(items)
        first = items[0]

        user = user_map.get(first['username'])
        if not user:
            print(f"   ⚠️  Skipping order {order_id} — user '{first['username']}' not found")
            skipped += 1
            continue

        if Order.objects.filter(id=int(order_id)).exists():
            skipped += 1
            continue

        order = Order.objects.create(
            id=int(order_id),
            user=user,
            cardholder_name=f"{user.first_name} {user.last_name}",
            card_last4='1234',
            billing_address='123 Test Street',
            city=first['city'],
            postcode=first['postcode'],
            delivery_date=first['delivery_date'],
            total_amount=sum(float(i['line_total']) for i in items),
            status=first['order_status'],
        )
        created_orders += 1

        for item in items:
            producer = producer_map.get(item['producer_name'])
            OrderItem.objects.create(
                order=order,
                producer=producer,
                product_name=item['product_name'],
                producer_name=item['producer_name'],
                unit_display=item['unit'],
                price=float(item['price_per_unit']),
                quantity=int(item['quantity']),
            )
            created_items += 1

        if created_orders % 100 == 0:
            print(f"   ... {created_orders} orders loaded")

    print(f"   ✅ {created_orders} orders and {created_items} items created, {skipped} skipped")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 55)
    print("  Bristol Regional Food Network — Database Loader")
    print("=" * 55)

    load_customers()
    load_producers()
    load_orders()

    print("\n" + "=" * 55)
    print("  ✅ All done! Your database is ready.")
    print("=" * 55)
