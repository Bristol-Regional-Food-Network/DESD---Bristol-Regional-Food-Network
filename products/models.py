from django.db import models
from producers.models import Producer


class Product(models.Model):
    SECTION_ALL = "all"
    SECTION_SEASONAL = "seasonal"
    SECTION_DISCOUNTED = "discounted"

    SECTION_CHOICES = [
        (SECTION_SEASONAL, "Seasonal Items"),
        (SECTION_DISCOUNTED, "Discounted Items"),
        (SECTION_ALL, "All Items"),
    ]

    producer = models.ForeignKey(
        Producer,
        on_delete=models.CASCADE,
        related_name="products"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    section = models.CharField(
        max_length=20,
        choices=SECTION_CHOICES,
        default=SECTION_ALL
    )
    discount_percent = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        if self.discount_percent and self.discount_percent > 0:
            return self.price * (100 - self.discount_percent) / 100
        return self.price