"""Tests for the users app.

Covers the UserProfile model (role assignment, helper predicates, string
representation) and the role_required decorator that protects role-scoped
views across the project.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse

from users.models import UserProfile
from users.decorators import role_required


class UserProfileModelTests(TestCase):
    """Unit tests for the UserProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="pw12345!"
        )

    def test_profile_links_to_user(self):
        profile = UserProfile.objects.create(user=self.user, role="customer")
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.role, "customer")

    def test_string_representation(self):
        profile = UserProfile.objects.create(user=self.user, role="producer")
        self.assertEqual(str(profile), "alice (producer)")

    def test_is_manager_predicate(self):
        customer = UserProfile.objects.create(user=self.user, role="customer")
        self.assertFalse(customer.is_manager())

        other = User.objects.create_user(username="bob", password="pw12345!")
        manager = UserProfile.objects.create(user=other, role="manager")
        self.assertTrue(manager.is_manager())

    def test_can_access_customer_rules(self):
        """Managers and customers can reach customer areas; producers cannot."""
        customer = UserProfile.objects.create(user=self.user, role="customer")
        other = User.objects.create_user(username="bob", password="pw12345!")
        producer = UserProfile.objects.create(user=other, role="producer")

        self.assertTrue(customer.can_access_customer())
        self.assertFalse(producer.can_access_customer())

    def test_can_access_producer_rules(self):
        """Managers and producers can reach producer areas; customers cannot."""
        customer = UserProfile.objects.create(user=self.user, role="customer")
        other = User.objects.create_user(username="bob", password="pw12345!")
        producer = UserProfile.objects.create(user=other, role="producer")

        self.assertTrue(producer.can_access_producer())
        self.assertFalse(customer.can_access_producer())

    def test_optional_fields_default_to_blank(self):
        profile = UserProfile.objects.create(user=self.user, role="customer")
        self.assertIn(profile.address, (None, ""))
        self.assertIn(profile.postcode, (None, ""))


class RoleRequiredDecoratorTests(TestCase):
    """Unit tests for the role_required decorator."""

    def setUp(self):
        self.factory = RequestFactory()

        @role_required("producer")
        def producer_only_view(request):
            return HttpResponse("ok")

        self.view = producer_only_view

    def _make_request(self, user):
        request = self.factory.get("/protected/")
        request.user = user
        return request

    def test_matching_role_allows_access(self):
        user = User.objects.create_user(username="prod", password="pw12345!")
        UserProfile.objects.create(user=user, role="producer")
        response = self.view(self._make_request(user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_manager_role_bypasses_role_check(self):
        """A manager is allowed through regardless of the required role,
        matching current decorator behaviour."""
        user = User.objects.create_user(username="mgr", password="pw12345!")
        UserProfile.objects.create(user=user, role="manager")
        response = self.view(self._make_request(user))
        self.assertEqual(response.status_code, 200)

    def test_mismatched_role_is_redirected_to_login(self):
        user = User.objects.create_user(username="cust", password="pw12345!")
        UserProfile.objects.create(user=user, role="customer")
        response = self.view(self._make_request(user))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_anonymous_user_is_redirected(self):
        response = self.view(self._make_request(AnonymousUser()))
        self.assertEqual(response.status_code, 302)
