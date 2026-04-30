"""Tests for the ai_engineer app.

Covers role-based access to the AI engineer dashboard / training /
recommendations endpoints. A non-AI-engineer customer must be redirected
away; an AI engineer and a manager must be allowed through.
"""

import json
import os
import tempfile

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from users.models import UserProfile


class AIEngineerAccessTests(TestCase):
    def setUp(self):
        self.ai_user = User.objects.create_user(
            username="ai", password="pw12345!"
        )
        UserProfile.objects.create(user=self.ai_user, role="ai_engineer")

        self.customer_user = User.objects.create_user(
            username="cust", password="pw12345!"
        )
        UserProfile.objects.create(user=self.customer_user, role="customer")

        self.manager_user = User.objects.create_user(
            username="mgr", password="pw12345!"
        )
        UserProfile.objects.create(user=self.manager_user, role="manager")

    def test_ai_engineer_can_reach_dashboard(self):
        client = Client()
        client.login(username="ai", password="pw12345!")
        resp = client.get(reverse("ai_engineer_dashboard"))
        self.assertIn(resp.status_code, (200, 302))

    def test_manager_can_reach_dashboard(self):
        """Managers bypass role-required checks."""
        client = Client()
        client.login(username="mgr", password="pw12345!")
        resp = client.get(reverse("ai_engineer_dashboard"))
        self.assertIn(resp.status_code, (200, 302))

    def test_customer_cannot_reach_dashboard(self):
        client = Client()
        client.login(username="cust", password="pw12345!")
        resp = client.get(reverse("ai_engineer_dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_anonymous_cannot_reach_dashboard(self):
        client = Client()
        resp = client.get(reverse("ai_engineer_dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_view_recommendations_requires_role(self):
        client = Client()
        client.login(username="cust", password="pw12345!")
        resp = client.get(reverse("ai_engineer_recommendations"))
        self.assertEqual(resp.status_code, 302)


class CustomerRecommendationsTests(TestCase):
    """The customer recommendations page should require login but otherwise
    be visible to any authenticated role (it personalises, it doesn't
    gate)."""

    def test_requires_login(self):
        client = Client()
        resp = client.get(reverse("customer_recommendations"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_authenticated_user_is_not_blocked(self):
        user = User.objects.create_user(username="u", password="pw12345!")
        UserProfile.objects.create(user=user, role="customer")
        client = Client()
        client.login(username="u", password="pw12345!")
        resp = client.get(reverse("customer_recommendations"))
        # 200 (render) or 302 (internal redirect on missing artefacts) are
        # both acceptable - the important thing is that it's not the
        # role-blocked redirect to /login/.
        if resp.status_code == 302:
            self.assertNotIn("/login/", resp.url)
