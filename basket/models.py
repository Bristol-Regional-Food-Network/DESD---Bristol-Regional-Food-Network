from django.conf import settings
from django.db import models
from products.models import Product
from producers.models import Producer


class Order(models.Model):
    STATUS_CHOICES = [
        ("paid", "Paid"),
        ("partially_fulfilled", "Partially Fulfilled"),
        ("cancelled", "Cancelled"),
        ("fulfilled", "Fulfilled"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="paid")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.username}"


class OrderItem(models.Model):
    FULFILMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("fulfilled", "Fulfilled"),
        ("cancelled", "Cancelled"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    fulfilment_status = models.CharField(
        max_length=20,
        choices=FULFILMENT_STATUS_CHOICES,
        default="pending",
    )

    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
