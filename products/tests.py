"""Tests for the products app.

Covers Product model pricing rules (discount, surplus discount, active
price fallback), seasonality logic, visibility rules, unit display
formatting, and the Review uniqueness constraint.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.utils import timezone

from producers.models import Producer
from products.models import Product, Review


def _make_producer(username="p1"):
    user = User.objects.create_user(username=username, password="pw12345!")
    return Producer.objects.create(user=user, display_name=f"Farm {username}")


class ProductPricingTests(TestCase):
    def setUp(self):
        self.producer = _make_producer()
        self.product = Product.objects.create(
            producer=self.producer,
            name="Carrots",
            price=Decimal("10.00"),
            stock=20,
        )

    def test_active_price_with_no_discount(self):
        self.assertEqual(self.product.active_price, Decimal("10.00"))

    def test_standard_discount_is_applied(self):
        self.product.discount_percent = 25
        self.product.save()
        self.assertEqual(self.product.active_price, Decimal("7.50"))
        self.assertEqual(self.product.discounted_price, Decimal("7.50"))

    def test_active_surplus_discount_overrides_standard(self):
        self.product.discount_percent = 20  # standard 20% → 8.00
        self.product.is_surplus = True
        self.product.surplus_discount_percent = 40  # surplus 40% → 6.00
        self.product.surplus_expires_at = timezone.now() + timedelta(hours=12)
        self.product.save()
        self.assertTrue(self.product.is_surplus_active)
        self.assertEqual(self.product.active_price, Decimal("6.00"))

    def test_expired_surplus_is_not_active(self):
        self.product.is_surplus = True
        self.product.surplus_discount_percent = 30
        self.product.surplus_expires_at = timezone.now() - timedelta(hours=1)
        self.product.save()
        self.assertFalse(self.product.is_surplus_active)
        self.assertEqual(self.product.active_price, Decimal("10.00"))

    def test_surplus_discount_outside_valid_band_is_ignored(self):
        self.product.is_surplus = True
        self.product.surplus_discount_percent = 5  # below 10 threshold
        self.product.surplus_expires_at = timezone.now() + timedelta(hours=12)
        self.product.save()
        self.assertFalse(self.product.is_surplus_active)

    def test_string_representation(self):
        self.assertEqual(str(self.product), "Carrots")


class ProductSeasonalityTests(TestCase):
    def setUp(self):
        self.producer = _make_producer()

    def _seasonal(self, start, end, stock=10):
        return Product.objects.create(
            producer=self.producer,
            name="Strawberries",
            price=Decimal("5.00"),
            stock=stock,
            availability_mode=Product.AVAILABILITY_SEASONAL,
            season_start_month=start,
            season_end_month=end,
        )

    def test_in_season_for_current_month(self):
        now = timezone.localdate().month
        product = self._seasonal(start=now, end=now)
        self.assertTrue(product.is_in_season())
        self.assertEqual(product.customer_status, "In Season")
        self.assertTrue(product.is_visible_to_customers)

    def test_out_of_season_hides_product(self):
        now = timezone.localdate().month
        other = 1 if now != 1 else 2
        product = self._seasonal(start=other, end=other)
        self.assertFalse(product.is_in_season())
        self.assertEqual(product.customer_status, "Out of Season")
        self.assertFalse(product.is_visible_to_customers)

    def test_season_wrapping_across_year(self):
        """Season Nov–Feb should include January."""
        product = self._seasonal(start=11, end=2)
        self.assertTrue(product.is_in_season(month=1))
        self.assertTrue(product.is_in_season(month=12))
        self.assertFalse(product.is_in_season(month=6))

    def test_unavailable_product_is_hidden(self):
        product = Product.objects.create(
            producer=self.producer,
            name="Hidden",
            price=Decimal("1.00"),
            stock=5,
            availability_mode=Product.AVAILABILITY_UNAVAILABLE,
        )
        self.assertFalse(product.is_visible_to_customers)
        self.assertEqual(product.customer_status, "Unavailable")

    def test_out_of_stock_is_hidden(self):
        product = Product.objects.create(
            producer=self.producer,
            name="Empty",
            price=Decimal("1.00"),
            stock=0,
        )
        self.assertFalse(product.is_visible_to_customers)
        self.assertEqual(product.customer_status, "Out of Stock")


class ProductUnitDisplayTests(TestCase):
    def setUp(self):
        self.producer = _make_producer()

    def _product(self, unit, unit_value):
        return Product.objects.create(
            producer=self.producer,
            name="Item",
            price=Decimal("1.00"),
            stock=1,
            unit=unit,
            unit_value=unit_value,
        )

    def test_each_unit_display(self):
        p = self._product(Product.UNIT_EACH, Decimal("1"))
        self.assertEqual(p.unit_display, "each")

    def test_kg_unit_display_trims_integer(self):
        p = self._product(Product.UNIT_KG, Decimal("2"))
        self.assertEqual(p.unit_display, "2 kg")

    def test_pack_unit_display(self):
        p = self._product(Product.UNIT_PACK, Decimal("6"))
        self.assertEqual(p.unit_display, "pack of 6")

    def test_price_display_formats(self):
        p = self._product(Product.UNIT_KG, Decimal("1"))
        self.assertEqual(p.price_display, "£1.00 per 1 kg")


class ReviewModelTests(TestCase):
    def setUp(self):
        self.producer = _make_producer()
        self.product = Product.objects.create(
            producer=self.producer,
            name="Bread",
            price=Decimal("3.00"),
            stock=5,
        )
        self.customer = User.objects.create_user(
            username="buyer", password="pw12345!"
        )

    def _make_review(self, rating=5):
        return Review.objects.create(
            product=self.product,
            customer=self.customer,
            rating=rating,
            title="Nice",
            review_text="Tasty bread.",
        )

    def test_review_is_created_and_counted(self):
        self._make_review()
        self.assertEqual(self.product.review_count, 1)
        self.assertEqual(self.product.average_rating, 5)

    def test_unique_review_per_customer_per_product(self):
        self._make_review()
        with self.assertRaises(IntegrityError):
            self._make_review(rating=4)

    def test_average_rating_computed_over_approved_only(self):
        other = User.objects.create_user(username="b", password="pw12345!")
        Review.objects.create(
            product=self.product, customer=self.customer,
            rating=5, title="a", review_text="b",
        )
        Review.objects.create(
            product=self.product, customer=other,
            rating=3, title="a", review_text="b", is_approved=False,
        )
        self.assertEqual(self.product.review_count, 1)
        self.assertEqual(self.product.average_rating, 5)


class ProductAllergenTests(TestCase):
    def setUp(self):
        self.producer = _make_producer("allergen-farm")

    def test_allergen_display_defaults_when_blank(self):
        product = Product.objects.create(
            producer=self.producer,
            name="Apples",
            price=Decimal("2.00"),
            stock=10,
            allergen_info="",
        )
        self.assertEqual(product.allergen_display, "No common allergens listed")
        self.assertFalse(product.has_allergen_warning)

    def test_allergen_warning_detects_entered_allergens(self):
        product = Product.objects.create(
            producer=self.producer,
            name="Walnut Bread",
            price=Decimal("3.50"),
            stock=8,
            allergen_info="Contains: Wheat (Gluten), Nuts (Walnuts)",
        )
        self.assertIn("Nuts", product.allergen_display)
        self.assertTrue(product.has_allergen_warning)

    def test_product_search_matches_allergen_text(self):
        Product.objects.create(
            producer=self.producer,
            name="Walnut Bread",
            price=Decimal("3.50"),
            stock=8,
            allergen_info="Contains: Wheat (Gluten), Nuts (Walnuts)",
        )
        Product.objects.create(
            producer=self.producer,
            name="Fresh Apples",
            price=Decimal("1.50"),
            stock=20,
            allergen_info="No common allergens listed",
        )

        response = self.client.get("/products/", {"q": "nuts"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Walnut Bread")
        self.assertNotContains(response, "Fresh Apples")

    def test_allergen_filter_can_show_no_common_allergens(self):
        Product.objects.create(
            producer=self.producer,
            name="Cheddar Cheese",
            price=Decimal("4.00"),
            stock=10,
            allergen_info="Contains: Milk",
        )
        Product.objects.create(
            producer=self.producer,
            name="Fresh Apples",
            price=Decimal("1.50"),
            stock=20,
            allergen_info="No common allergens listed",
        )

        response = self.client.get("/products/", {"allergen": "no_common_allergens"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fresh Apples")
        self.assertNotContains(response, "Cheddar Cheese")
