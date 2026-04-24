"""Tests for the producers app.

Covers the Producer model (field defaults, optional coordinates, string
representation) and the URL routing contract for the producer area.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse, NoReverseMatch

from producers.models import Producer


class ProducerModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="farmer", password="pw12345!"
        )

    def test_required_fields(self):
        producer = Producer.objects.create(
            user=self.user,
            display_name="Green Fields Farm",
        )
        self.assertEqual(producer.display_name, "Green Fields Farm")
        self.assertEqual(producer.user, self.user)
        self.assertEqual(producer.bio, "")
        self.assertEqual(producer.location, "")
        self.assertEqual(producer.postcode, "")

    def test_string_representation_uses_display_name(self):
        producer = Producer.objects.create(
            user=self.user, display_name="Sunny Orchard"
        )
        self.assertEqual(str(producer), "Sunny Orchard")

    def test_optional_coordinates_allow_null(self):
        producer = Producer.objects.create(
            user=self.user, display_name="Test"
        )
        self.assertIsNone(producer.latitude)
        self.assertIsNone(producer.longitude)

    def test_stored_coordinates_round_trip(self):
        producer = Producer.objects.create(
            user=self.user,
            display_name="GPS Farm",
            latitude=51.4545,
            longitude=-2.5879,
        )
        producer.refresh_from_db()
        self.assertAlmostEqual(producer.latitude, 51.4545, places=4)
        self.assertAlmostEqual(producer.longitude, -2.5879, places=4)

    def test_multiple_producers_coexist(self):
        Producer.objects.create(user=self.user, display_name="First")
        other = User.objects.create_user(
            username="other", password="pw12345!"
        )
        Producer.objects.create(user=other, display_name="Second")
        self.assertEqual(Producer.objects.count(), 2)


class ProducerUrlTests(TestCase):
    def test_named_urls_resolve(self):
        """All named URLs in the producers app must resolve."""
        self.assertTrue(reverse("producers:producer_dashboard"))
        self.assertTrue(reverse("producers:list"))
        self.assertTrue(reverse("producers:producer_orders"))

    def test_detail_url_encodes_id(self):
        url = reverse("producers:detail", args=[42])
        self.assertIn("42", url)

    def test_unknown_named_url_raises(self):
        with self.assertRaises(NoReverseMatch):
            reverse("producers:does_not_exist")
