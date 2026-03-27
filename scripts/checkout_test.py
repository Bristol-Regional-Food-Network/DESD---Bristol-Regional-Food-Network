import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from products.models import Product
from django.utils import timezone
from datetime import timedelta
import traceback

c = Client()
try:
    user = User.objects.filter(username='manager').first() or User.objects.filter(username='adham').first() or User.objects.first()
    if not user:
        print('No user found; cannot login')
    else:
        c.force_login(user)
        p = Product.objects.filter(id=2).first() or Product.objects.filter().first()
        if not p:
            print('No product found')
        else:
            session = c.session
            session['customer_postcode'] = 'BS1'
            session['basket'] = {
                str(p.id): {
                    'name': p.name,
                    'price': float(p.active_price),
                    'quantity': 1,
                    'producer': getattr(p.producer, 'display_name', ''),
                    'producer_postcode': getattr(p.producer, 'postcode', ''),
                    'unit_display': getattr(p, 'unit_display', 'each')
                }
            }
            session.save()
            card = {
                'cardholder_name': f'{user.first_name} {user.last_name}'.strip() or 'Test User',
                'card_number': '4242424242424242',
                'expiry_month': 12,
                'expiry_year': 99,
                'cvv': '123',
                'billing_address': '1 Test St',
                'city': 'Bristol',
                'postcode': 'BS1 1AA',
                'country': 'UK'
            }
            from django.utils.text import slugify
            producer_key = slugify(getattr(p.producer, 'display_name', '') or str(p.producer))
            delivery_field = f'delivery_date_{producer_key}'
            delivery_date = (timezone.localdate() + timedelta(days=3)).isoformat()
            card[delivery_field] = delivery_date

            print('Posting checkout for product', p.id, 'as user', user.username)
            try:
                # supply HTTP_HOST to avoid DisallowedHost when using test client
                resp = c.post('/basket/checkout/', card, HTTP_HOST='localhost')
                print('Status:', resp.status_code)
                print('Templates:', [t.name for t in resp.templates])
                if resp.status_code >= 400:
                    print('Content:\n', resp.content.decode('utf-8')[:2000])
            except Exception:
                print('POST raised exception:')
                traceback.print_exc()
except Exception:
    traceback.print_exc()
