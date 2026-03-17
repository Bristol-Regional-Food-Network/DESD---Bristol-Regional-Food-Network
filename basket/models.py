from django.db import models
from django.contrib.auth.models import User


class Order(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("paid", "Paid"),
		("shipped", "Shipped"),
		("cancelled", "Cancelled"),
	]

	customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	notes = models.TextField(blank=True)

	def __str__(self):
		return f"Order #{self.id} — {self.customer.username} — {self.total_amount}"
