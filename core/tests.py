"""Tests for the core app.

Covers the public home page, post-login routing, and the CustomerProfile
/ ProducerProfile auxiliary models.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from users.models import UserProfile
from core.models import CustomerProfile, ProducerProfile


class HomeViewTests(TestCase):
    def test_home_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)


class PostLoginRedirectTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_customer_redirected_to_products(self):
        user = User.objects.create_user(
            username="cust", password="pw12345!"
        )
        UserProfile.objects.create(user=user, role="customer")
        self.client.login(username="cust", password="pw12345!")
        resp = self.client.get(reverse("post_login_redirect"))
        self.assertEqual(resp.status_code, 302)

    def test_manager_redirected_to_dashboard(self):
        user = User.objects.create_user(
            username="mgr", password="pw12345!"
        )
        UserProfile.objects.create(user=user, role="manager")
        self.client.login(username="mgr", password="pw12345!")
        resp = self.client.get(reverse("post_login_redirect"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("manager", resp.url)

    def test_anonymous_post_login_redirects_to_login(self):
        resp = self.client.get(reverse("post_login_redirect"))
        self.assertEqual(resp.status_code, 302)


class ProfileModelTests(TestCase):
    def test_customer_profile_string(self):
        user = User.objects.create_user(username="a", password="pw12345!")
        profile = CustomerProfile.objects.create(user=user)
        self.assertEqual(str(profile), "Customer: a")

    def test_producer_profile_string(self):
        user = User.objects.create_user(username="b", password="pw12345!")
        profile = ProducerProfile.objects.create(
            user=user, farm_name="Sunny Farm"
        )
        self.assertEqual(str(profile), "Producer: Sunny Farm")
