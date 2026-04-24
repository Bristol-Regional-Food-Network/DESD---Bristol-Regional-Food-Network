"""Tests for the basket app.

Covers the Order / OrderItem domain model (subtotal and line-total
properties, status defaults, string representation), the PaymentForm
validation rules, and the core session-based basket add/update/remove
workflow through Django's test client.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from producers.models import Producer
from products.models import Product
from basket.models import Order, OrderItem, ProducerOrder
from basket.forms import PaymentForm


def _producer():
    user = User.objects.create_user(username="farmer", password="pw12345!")
    return Producer.objects.create(user=user, display_name="Farm",
                                   postcode="BS1 1AA",
                                   latitude=51.45, longitude=-2.59)


def _product(producer, **overrides):
    defaults = dict(
        producer=producer,
        name="Apples",
        price=Decimal("4.00"),
        stock=10,
    )
    defaults.update(overrides)
    return Product.objects.create(**defaults)


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer", password="pw12345!"
        )
        self.order = Order.objects.create(
            user=self.user,
            cardholder_name="Test Buyer",
            card_last4="4242",
            billing_address="1 Test St",
            city="Bristol",
            postcode="BS1 1AA",
            delivery_date=date(2026, 5, 1),
            total_amount=Decimal("10.00"),
        )

    def test_default_status_is_pending(self):
        self.assertEqual(self.order.status, Order.STATUS_PENDING)

    def test_default_country_is_uk(self):
        self.assertEqual(self.order.country, "UK")

    def test_string_uses_username(self):
        self.assertIn("buyer", str(self.order))

    def test_string_falls_back_to_cardholder_when_user_deleted(self):
        self.order.user = None
        self.order.save()
        self.assertIn("Test Buyer", str(self.order))


class OrderItemTests(TestCase):
    def setUp(self):
        self.producer = _producer()
        self.product = _product(self.producer)
        self.user = User.objects.create_user(
            username="buyer", password="pw12345!"
        )
        self.order = Order.objects.create(
            user=self.user,
            cardholder_name="Buyer",
            card_last4="1234",
            billing_address="x",
            city="Bristol",
            postcode="BS1",
            delivery_date=date(2026, 5, 1),
            total_amount=Decimal("8.00"),
        )

    def test_subtotal_multiplies_price_and_quantity(self):
        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            producer=self.producer,
            product_name="Apples",
            price=Decimal("4.00"),
            quantity=2,
        )
        self.assertEqual(item.subtotal, Decimal("8.00"))
        self.assertEqual(item.line_total, Decimal("8.00"))

    def test_subtotal_handles_missing_price(self):
        item = OrderItem.objects.create(
            order=self.order,
            product=None,
            product_name="Apples",
            price=None,
            quantity=3,
        )
        self.assertEqual(item.subtotal, Decimal("0.00"))
        self.assertEqual(item.unit_price, Decimal("0.00"))

    def test_default_fulfilment_status(self):
        item = OrderItem.objects.create(
            order=self.order,
            product_name="X",
            price=Decimal("1"),
            quantity=1,
        )
        self.assertEqual(item.fulfilment_status,
                         OrderItem.FULFILMENT_STATUS_PENDING)


class ProducerOrderTests(TestCase):
    def test_string_includes_producer_and_order_id(self):
        user = User.objects.create_user(username="u", password="pw12345!")
        order = Order.objects.create(
            user=user, cardholder_name="x", card_last4="1234",
            billing_address="x", city="x", postcode="x",
            delivery_date=date(2026, 5, 1),
            total_amount=Decimal("1"),
        )
        po = ProducerOrder.objects.create(
            order=order,
            producer_name="Farm",
            delivery_date=date(2026, 5, 2),
        )
        self.assertIn("Farm", str(po))
        self.assertIn(str(order.id), str(po))


class PaymentFormTests(TestCase):
    def _valid_payload(self):
        next_year = (datetime.now().year + 1) % 100
        return {
            "cardholder_name": "Test Buyer",
            "card_number": "4242424242424242",
            "expiry_month": 12,
            "expiry_year": next_year,
            "cvv": "123",
            "billing_address": "1 Test St",
            "city": "Bristol",
            "postcode": "BS1 1AA",
            "country": "UK",
        }

    def test_valid_form(self):
        form = PaymentForm(data=self._valid_payload())
        self.assertTrue(form.is_valid(), form.errors)

    def test_card_number_must_be_digits(self):
        data = self._valid_payload()
        data["card_number"] = "4242-4242-4242-abcd"
        form = PaymentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("card_number", form.errors)

    def test_card_number_wrong_length(self):
        data = self._valid_payload()
        data["card_number"] = "4242"
        form = PaymentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("card_number", form.errors)

    def test_cvv_must_be_digits(self):
        data = self._valid_payload()
        data["cvv"] = "abc"
        form = PaymentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("cvv", form.errors)

    def test_expired_card_rejected(self):
        data = self._valid_payload()
        data["expiry_year"] = 0  # year 2000
        data["expiry_month"] = 1
        form = PaymentForm(data=data)
        self.assertFalse(form.is_valid())


class BasketFlowTests(TestCase):
    def setUp(self):
        self.producer = _producer()
        self.product = _product(self.producer)
        self.user = User.objects.create_user(
            username="buyer", password="pw12345!"
        )
        self.client = Client()
        self.client.login(username="buyer", password="pw12345!")

    def test_basket_add_adds_product_to_session(self):
        url = reverse("basket:basket_add", args=[self.product.id])
        resp = self.client.post(url, {"quantity": 2})
        self.assertEqual(resp.status_code, 302)
        basket = self.client.session.get("basket", {})
        self.assertIn(str(self.product.id), basket)
        self.assertEqual(basket[str(self.product.id)]["quantity"], 2)

    def test_basket_add_caps_at_stock(self):
        url = reverse("basket:basket_add", args=[self.product.id])
        self.client.post(url, {"quantity": 999})  # stock=10
        basket = self.client.session.get("basket", {})
        self.assertEqual(basket[str(self.product.id)]["quantity"], 10)

    def test_basket_remove_clears_item(self):
        add_url = reverse("basket:basket_add", args=[self.product.id])
        self.client.post(add_url, {"quantity": 1})
        remove_url = reverse("basket:basket_remove",
                             args=[self.product.id])
        self.client.post(remove_url)
        basket = self.client.session.get("basket", {})
        self.assertNotIn(str(self.product.id), basket)

    def test_basket_detail_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("basket:basket_detail"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)
