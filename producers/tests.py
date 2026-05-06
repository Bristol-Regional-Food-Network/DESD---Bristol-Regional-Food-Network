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

from datetime import date
from decimal import Decimal

from basket.models import Order, OrderItem, ProducerOrder, OrderStatusHistory
from producers.views import _build_grouped_orders, _producer_settlement_data


class ProducerOrderReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="settlement_farmer", password="pw12345!")
        self.user.userprofile.role = "producer"
        self.user.userprofile.save()
        self.producer = self.user.producer
        self.product = self.producer.products.create(
            name="Eggs",
            price=Decimal("3.50"),
            stock=20,
            allergen_info="Contains: Eggs",
        )
        self.customer = User.objects.create_user(username="buyer", password="pw12345!")
        self.order = Order.objects.create(
            user=self.customer,
            producer_name=self.producer.display_name,
            cardholder_name="Buyer User",
            card_last4="4242",
            billing_address="1 Test Street",
            city="Bristol",
            postcode="BS1 4DJ",
            country="UK",
            delivery_date=date.today(),
            total_amount=Decimal("10.50"),
            commission_amount=Decimal("0.53"),
            producer_amount=Decimal("9.98"),
            status=Order.STATUS_FULFILLED,
        )
        self.producer_order = ProducerOrder.objects.create(
            order=self.order,
            producer_name=self.producer.display_name,
            delivery_date=date.today(),
            subtotal_amount=Decimal("10.50"),
            payout_amount=Decimal("9.98"),
        )

    def test_grouped_orders_use_line_total_property_without_crashing(self):
        item = OrderItem.objects.create(
            order=self.order,
            producer_order=self.producer_order,
            product=self.product,
            producer=self.producer,
            product_name="Eggs",
            producer_name=self.producer.display_name,
            price=Decimal("3.50"),
            quantity=3,
            fulfilment_status=OrderItem.FULFILMENT_STATUS_FULFILLED,
        )

        grouped = _build_grouped_orders([item])

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["producer_total"], Decimal("10.50"))

    def test_settlement_totals_use_only_current_producer_fulfilled_items(self):
        OrderItem.objects.create(
            order=self.order,
            producer_order=self.producer_order,
            product=self.product,
            producer=self.producer,
            product_name="Eggs",
            producer_name=self.producer.display_name,
            price=Decimal("3.50"),
            quantity=2,
            fulfilment_status=OrderItem.FULFILMENT_STATUS_FULFILLED,
        )
        OrderItem.objects.create(
            order=self.order,
            producer_order=self.producer_order,
            product=self.product,
            producer=self.producer,
            product_name="Pending Eggs",
            producer_name=self.producer.display_name,
            price=Decimal("3.50"),
            quantity=10,
            fulfilment_status=OrderItem.FULFILMENT_STATUS_PENDING,
        )

        settlements, rows = _producer_settlement_data(self.producer)

        self.assertEqual(len(settlements), 1)
        self.assertEqual(len(rows), 1)

        summary = settlements[0]
        self.assertEqual(summary["gross_sales"], Decimal("7.00"))
        self.assertEqual(summary["commission"], Decimal("0.35"))
        self.assertEqual(summary["payout"], Decimal("6.65"))

    def test_settlement_csv_downloads_for_logged_in_producer(self):
        OrderItem.objects.create(
            order=self.order,
            producer_order=self.producer_order,
            product=self.product,
            producer=self.producer,
            product_name="Eggs",
            producer_name=self.producer.display_name,
            price=Decimal("3.50"),
            quantity=2,
            fulfilment_status=OrderItem.FULFILMENT_STATUS_FULFILLED,
        )
        self.client.login(username="settlement_farmer", password="pw12345!")

        response = self.client.get(reverse("producers:producer_settlement_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("Network Commission 5%", content)
        self.assertIn("Producer Payout 95%", content)
        self.assertIn("Eggs", content)


class ProducerOrderStatusHistoryTests(TestCase):
    def setUp(self):
        self.producer_user = User.objects.create_user(username="status_farmer", password="pw12345!")
        self.producer_user.userprofile.role = "producer"
        self.producer_user.userprofile.save()
        self.producer = self.producer_user.producer
        self.producer.display_name = "Status Farm"
        self.producer.save()

        self.other_user = User.objects.create_user(username="other_farmer", password="pw12345!")
        self.other_user.userprofile.role = "producer"
        self.other_user.userprofile.save()
        self.other_producer = self.other_user.producer
        self.other_producer.display_name = "Other Farm"
        self.other_producer.save()

        self.customer = User.objects.create_user(username="status_buyer", password="pw12345!")
        self.product = self.producer.products.create(
            name="Carrots",
            price=Decimal("2.00"),
            stock=10,
            allergen_info="No common allergens listed",
        )
        self.other_product = self.other_producer.products.create(
            name="Milk",
            price=Decimal("3.00"),
            stock=10,
            allergen_info="Contains: Milk",
        )
        self.order = Order.objects.create(
            user=self.customer,
            producer_name="Multiple Producers",
            cardholder_name="Buyer User",
            card_last4="4242",
            billing_address="1 Test Street",
            city="Bristol",
            postcode="BS1 4DJ",
            country="UK",
            delivery_date=date.today(),
            special_delivery_instructions="Deliver to the kitchen entrance.",
            total_amount=Decimal("5.00"),
            status=Order.STATUS_PENDING,
        )
        self.producer_order = ProducerOrder.objects.create(
            order=self.order,
            producer_name=self.producer.display_name,
            delivery_date=date.today(),
            subtotal_amount=Decimal("2.00"),
            payout_amount=Decimal("1.90"),
        )
        self.other_producer_order = ProducerOrder.objects.create(
            order=self.order,
            producer_name=self.other_producer.display_name,
            delivery_date=date.today(),
            subtotal_amount=Decimal("3.00"),
            payout_amount=Decimal("2.85"),
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            producer_order=self.producer_order,
            product=self.product,
            producer=self.producer,
            product_name="Carrots",
            producer_name=self.producer.display_name,
            price=Decimal("2.00"),
            quantity=1,
        )
        self.other_item = OrderItem.objects.create(
            order=self.order,
            producer_order=self.other_producer_order,
            product=self.other_product,
            producer=self.other_producer,
            product_name="Milk",
            producer_name=self.other_producer.display_name,
            price=Decimal("3.00"),
            quantity=1,
        )

    def test_updating_item_status_creates_history_entry_with_note(self):
        self.client.login(username="status_farmer", password="pw12345!")

        response = self.client.post(
            reverse("producers:update_order_item_status", args=[self.item.id]),
            {
                "fulfilment_status": OrderItem.FULFILMENT_STATUS_FULFILLED,
                "status_note": "Products are ready for delivery.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.fulfilment_status, OrderItem.FULFILMENT_STATUS_FULFILLED)

        history = self.item.status_history.get()
        self.assertEqual(history.old_status, OrderItem.FULFILMENT_STATUS_PENDING)
        self.assertEqual(history.new_status, OrderItem.FULFILMENT_STATUS_FULFILLED)
        self.assertEqual(history.note, "Products are ready for delivery.")
        self.assertEqual(history.changed_by, self.producer_user)
        self.assertIsNotNone(history.created_at)

    def test_producer_cannot_update_another_producers_item(self):
        self.client.login(username="status_farmer", password="pw12345!")

        response = self.client.post(
            reverse("producers:update_order_item_status", args=[self.other_item.id]),
            {"fulfilment_status": OrderItem.FULFILMENT_STATUS_FULFILLED},
        )

        self.assertEqual(response.status_code, 404)
        self.other_item.refresh_from_db()
        self.assertEqual(self.other_item.fulfilment_status, OrderItem.FULFILMENT_STATUS_PENDING)

    def test_producer_order_detail_displays_history_and_delivery_instructions(self):
        OrderStatusHistory.objects.create(
            order=self.order,
            order_item=self.item,
            producer_order=self.producer_order,
            old_status=OrderItem.FULFILMENT_STATUS_PENDING,
            new_status=OrderItem.FULFILMENT_STATUS_FULFILLED,
            note="Packed and ready.",
            changed_by=self.producer_user,
        )
        self.client.login(username="status_farmer", password="pw12345!")

        response = self.client.get(reverse("producers:producer_order_detail", args=[self.order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Packed and ready.")
        self.assertContains(response, "Deliver to the kitchen entrance.")
        self.assertContains(response, "Status History")
