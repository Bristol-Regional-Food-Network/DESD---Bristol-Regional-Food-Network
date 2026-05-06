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

    producer_name = models.CharField(max_length=120, blank=True)

    cardholder_name = models.CharField(max_length=100)
    card_last4 = models.CharField(max_length=4)

    billing_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="UK")
    special_delivery_instructions = models.TextField(blank=True, default="")

    delivery_date = models.DateField()
    payment_reference = models.CharField(max_length=50, blank=True, default="")

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )
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

    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
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
        price = self.price if self.price is not None else Decimal("0.00")
        quantity = self.quantity if self.quantity is not None else 0
        return price * quantity

    @property
    def unit_price(self):
        return self.price if self.price is not None else Decimal("0.00")

    @property
    def line_total(self):
        price = self.price if self.price is not None else Decimal("0.00")
        quantity = self.quantity if self.quantity is not None else 0
        return quantity * price




class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="status_history",
        null=True,
        blank=True,
    )
    producer_order = models.ForeignKey(
        ProducerOrder,
        on_delete=models.CASCADE,
        related_name="status_history",
        null=True,
        blank=True,
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    note = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_updates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_id}: {self.old_status} → {self.new_status}"

# ---------------------------------------------------------------------------
# Recurring orders (TC-018)
# Allows restaurant / business customers to set up a repeating template that
# automatically generates new orders on a weekly or fortnightly schedule.
# ---------------------------------------------------------------------------
class RecurringOrder(models.Model):
    FREQ_WEEKLY = "weekly"
    FREQ_FORTNIGHTLY = "fortnightly"

    FREQUENCY_CHOICES = [
        (FREQ_WEEKLY, "Every week"),
        (FREQ_FORTNIGHTLY, "Every two weeks"),
    ]

    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recurring_orders",
    )
    name = models.CharField(max_length=120, default="Weekly order")

    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default=FREQ_WEEKLY)
    order_day = models.IntegerField(choices=DAY_CHOICES, default=0)         # day order is generated
    delivery_day = models.IntegerField(choices=DAY_CHOICES, default=2)      # day items are delivered

    # Billing / delivery snapshot (mirrors the original Order so we can re-bill)
    cardholder_name = models.CharField(max_length=100)
    card_last4 = models.CharField(max_length=4)
    billing_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="UK")

    next_run_date = models.DateField()
    next_delivery_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recurring {self.frequency} order #{self.id} ({self.user.username})"

    @property
    def template_total(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))


class RecurringOrderItem(models.Model):
    """A line in a recurring order template. Stays attached to the template
    and is copied (and optionally edited per-instance via the *next_quantity*
    override) when the next order is generated."""

    recurring_order = models.ForeignKey(
        RecurringOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    producer = models.ForeignKey(
        Producer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    product_name = models.CharField(max_length=200)
    producer_name = models.CharField(max_length=120, blank=True)
    unit_display = models.CharField(max_length=50, default="each")

    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    # Override applied only to the *next* generated instance, then cleared.
    # Lets restaurants tweak one week's order without changing the template.
    next_quantity_override = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def effective_next_quantity(self):
        return self.next_quantity_override if self.next_quantity_override is not None else self.quantity

    @property
    def line_total(self):
        price = self.price if self.price is not None else Decimal("0.00")
        return price * self.quantity