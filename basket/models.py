from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from products.models import Product
from producers.models import Producer


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PARTIALLY_FULFILLED = "partially_fulfilled"
    STATUS_CANCELLED = "cancelled"
    STATUS_FULFILLED = "fulfilled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_PARTIALLY_FULFILLED, "Partially Fulfilled"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_FULFILLED, "Fulfilled"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders"
    )

    # For single-producer orders this can hold the producer name.
    # For multi-producer orders use "Multiple Producers".
    producer_name = models.CharField(max_length=120, blank=True)

    cardholder_name = models.CharField(max_length=100)
    card_last4 = models.CharField(max_length=4)

    billing_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="UK")

    # Parent order stores an overall/earliest delivery date.
    delivery_date = models.DateField()
    payment_reference = models.CharField(max_length=50, blank=True, default="")

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
    # Total producer payout across all producer sub-orders.
    producer_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_display = self.user.username if self.user else self.cardholder_name
        return f"Order #{self.id} - {user_display}"


class ProducerOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_READY = "ready"
    STATUS_DELIVERED = "delivered"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_READY, "Ready"),
        (STATUS_DELIVERED, "Delivered"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="producer_orders")
    producer_name = models.CharField(max_length=120)
    delivery_date = models.DateField()
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    def __str__(self):
        return f"Order #{self.order_id} - {self.producer_name}"


class OrderItem(models.Model):
    FULFILMENT_STATUS_PENDING = "pending"
    FULFILMENT_STATUS_FULFILLED = "fulfilled"
    FULFILMENT_STATUS_CANCELLED = "cancelled"

    FULFILMENT_STATUS_CHOICES = [
        (FULFILMENT_STATUS_PENDING, "Pending"),
        (FULFILMENT_STATUS_FULFILLED, "Fulfilled"),
        (FULFILMENT_STATUS_CANCELLED, "Cancelled"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    producer_order = models.ForeignKey(
        ProducerOrder,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    # Added so producer order/report pages can directly query producer-owned items
    producer = models.ForeignKey(
        Producer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )

    product_name = models.CharField(max_length=200)
    producer_name = models.CharField(max_length=120, blank=True)
    unit_display = models.CharField(max_length=50, default="each")

    # Keep Branch A field name for compatibility with current checkout code
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    fulfilment_status = models.CharField(
        max_length=20,
        choices=FULFILMENT_STATUS_CHOICES,
        default=FULFILMENT_STATUS_PENDING,
    )

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity

    @property
    def unit_price(self):
        return self.price

    def line_total(self):
        return self.quantity * self.price