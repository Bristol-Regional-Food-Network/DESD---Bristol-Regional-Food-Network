"""
===============================================================
  Bristol Regional Food Network — Master Database Loader
===============================================================
  Run this script to populate the database with all data.

<<<<<<< HEAD
  Required files (place in same folder as this script):
=======
  Required files:
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
    - customers_dataset.csv
    - producers_dataset.csv
    - orders_dataset.csv

  Usage:
<<<<<<< HEAD
      python load_all.py

  Make sure you have activated your virtual environment first:
      .venv\Scripts\Activate.ps1  (Windows)
      source .venv/bin/activate   (Mac/Linux)
=======
      python DATA/load_all.py
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
===============================================================
"""

import os
<<<<<<< HEAD
import django
=======
import sys
import csv
import django
from itertools import groupby

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

sys.path.insert(0, PROJECT_ROOT)
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

<<<<<<< HEAD
import csv
from itertools import groupby
from django.contrib.auth.models import User
from basket.models import Order, OrderItem
from producers.models import Producer
=======
from django.contrib.auth.models import User
from basket.models import Order, OrderItem
from producers.models import Producer
from products.models import Product
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1

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
<<<<<<< HEAD
=======

>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
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
<<<<<<< HEAD
=======

>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
            user = User.objects.create_user(
                username=row['username'],
                email=row['email'],
                password=row['password'],
                first_name=row['first_name'],
                last_name=row['last_name'],
            )
<<<<<<< HEAD
=======

>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
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
<<<<<<< HEAD
#  STEP 3 — LOAD ORDERS
=======
#  STEP 3 — LOAD PRODUCTS
# ══════════════════════════════════════════════════════════════

def load_products():
    print("\n📦 Loading products from orders dataset...")
    path = os.path.join(BASE_DIR, 'orders_dataset.csv')
    created = skipped = 0

    category_map = {
        'vegetables': Product.CATEGORY_VEGETABLES,
        'fruits': Product.CATEGORY_FRUITS,
        'dairy': Product.CATEGORY_DAIRY,
        'bakery': Product.CATEGORY_BAKERY,
        'preserves': Product.CATEGORY_PRESERVES,
        'seasonal_specialities': Product.CATEGORY_SEASONAL_SPECIALITIES,
        'seasonal specialities': Product.CATEGORY_SEASONAL_SPECIALITIES,
    }

    section_map = {
        'all': Product.SECTION_ALL,
        'seasonal': Product.SECTION_SEASONAL,
        'discounted': Product.SECTION_DISCOUNTED,
        'surplus': Product.SECTION_SURPLUS,
    }

    with open(path, encoding='utf-8') as f:
        rows = csv.DictReader(f)

        for row in rows:
            producer = Producer.objects.filter(display_name=row['producer_name']).first()
            if not producer:
                skipped += 1
                continue

            name = row['product_name'].strip()

            if Product.objects.filter(name=name, producer=producer).exists():
                skipped += 1
                continue

            category_raw = (row.get('category') or '').strip().lower()
            section_raw = (row.get('section') or 'all').strip().lower()
            unit_raw = (row.get('unit') or 'each').strip().lower()

            valid_units = {choice[0] for choice in Product.UNIT_CHOICES}
            if unit_raw not in valid_units:
                unit_raw = Product.UNIT_EACH

            Product.objects.create(
                producer=producer,
                name=name,
                description=f"{name} from {producer.display_name}",
                price=row.get('price_per_unit') or 0,
                stock=25,
                is_organic=str(row.get('is_organic', '')).strip().lower() == 'true',
                unit=unit_raw,
                unit_value=1,
                category=category_map.get(category_raw, Product.CATEGORY_VEGETABLES),
                section=section_map.get(section_raw, Product.SECTION_ALL),
                availability_mode=Product.AVAILABILITY_YEAR_ROUND,
                discount_percent=10 if section_raw == 'discounted' else 0,
                is_surplus=(section_raw == 'surplus'),
                surplus_discount_percent=20 if section_raw == 'surplus' else 0,
            )
            created += 1

    print(f"   ✅ {created} products created, {skipped} skipped")


# ══════════════════════════════════════════════════════════════
#  STEP 4 — LOAD ORDERS
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
# ══════════════════════════════════════════════════════════════

def load_orders():
    print("\n🛒 Loading orders...")
    path = os.path.join(BASE_DIR, 'orders_dataset.csv')
    created_orders = created_items = skipped = 0

    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

<<<<<<< HEAD
    user_map     = {u.username: u for u in User.objects.all()}
=======
    user_map = {u.username: u for u in User.objects.all()}
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
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
<<<<<<< HEAD
=======

>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
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
<<<<<<< HEAD
=======
    load_products()
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
    load_orders()

    print("\n" + "=" * 55)
    print("  ✅ All done! Your database is ready.")
<<<<<<< HEAD
    print("=" * 55)
=======
    print("=" * 55)
>>>>>>> c216a0b07d3bb60dfb0a693e37482989204868b1
