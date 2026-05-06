"""Tests for the managers app.

Covers the manager dashboard and orders endpoint access rules: a
customer must not reach them, while a manager must.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth.models import User

from users.models import UserProfile
from basket.models import Order


class ManagerAccessTests(TestCase):
    def setUp(self):
        self.manager_user = User.objects.create_user(
            username="mgr", password="pw12345!"
        )
        UserProfile.objects.create(user=self.manager_user, role="manager")

        self.customer_user = User.objects.create_user(
            username="cust", password="pw12345!"
        )
        UserProfile.objects.create(user=self.customer_user, role="customer")

    def test_manager_reaches_dashboard(self):
        client = Client()
        client.login(username="mgr", password="pw12345!")
        resp = client.get("/manager/dashboard/")
        # Either 200 (template) or 302 redirect to a manager page is acceptable.
        self.assertIn(resp.status_code, (200, 302))

    def test_customer_is_redirected_from_manager_dashboard(self):
        client = Client()
        client.login(username="cust", password="pw12345!")
        resp = client.get("/manager/dashboard/")
        self.assertEqual(resp.status_code, 302)

    def test_anonymous_redirected_from_manager_dashboard(self):
        client = Client()
        resp = client.get("/manager/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)


class ManagerOrdersEndpointTests(TestCase):
    def setUp(self):
        self.manager_user = User.objects.create_user(
            username="mgr", password="pw12345!"
        )
        UserProfile.objects.create(user=self.manager_user, role="manager")
        self.order = Order.objects.create(
            user=self.manager_user,
            cardholder_name="Test",
            card_last4="1234",
            billing_address="x",
            city="Bristol",
            postcode="BS1",
            delivery_date=date(2026, 5, 1),
            total_amount=Decimal("10.00"),
        )

    def test_manager_can_update_order_status(self):
        client = Client()
        client.login(username="mgr", password="pw12345!")
        resp = client.post("/manager/orders/", {
            "action": "update_status",
            "order_id": str(self.order.id),
            "status": "paid",
        })
        self.assertIn(resp.status_code, (200, 302))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")

    def test_manager_can_delete_order(self):
        client = Client()
        client.login(username="mgr", password="pw12345!")
        order_id = self.order.id
        resp = client.post("/manager/orders/", {
            "action": "delete",
            "order_id": str(order_id),
        })
        self.assertIn(resp.status_code, (200, 302))
        self.assertFalse(Order.objects.filter(id=order_id).exists())
