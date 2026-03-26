from decimal import Decimal
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

    CATEGORY_VEGETABLES = "vegetables"
    CATEGORY_DAIRY = "dairy"
    CATEGORY_BAKERY = "bakery"
    CATEGORY_PRESERVES = "preserves"
    CATEGORY_FRUITS = "fruits"
    CATEGORY_SEASONAL_SPECIALITIES = "seasonal_specialities"

    CATEGORY_CHOICES = [
        (CATEGORY_VEGETABLES, "Vegetables"),
        (CATEGORY_DAIRY, "Dairy Products"),
        (CATEGORY_BAKERY, "Bakery Goods"),
        (CATEGORY_PRESERVES, "Preserves"),
        (CATEGORY_FRUITS, "Fruits"),
        (CATEGORY_SEASONAL_SPECIALITIES, "Seasonal Specialities"),
    ]

    UNIT_EACH = "each"
    UNIT_G = "g"
    UNIT_KG = "kg"
    UNIT_ML = "ml"
    UNIT_L = "l"
    UNIT_PACK = "pack"

    UNIT_CHOICES = [
        (UNIT_EACH, "Each"),
        (UNIT_G, "Grams (g)"),
        (UNIT_KG, "Kilograms (kg)"),
        (UNIT_ML, "Millilitres (ml)"),
        (UNIT_L, "Litres (l)"),
        (UNIT_PACK, "Pack"),
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

    unit_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1,
        help_text="Example: 500 for 500g, 1 for 1kg, 6 for pack of 6"
    )
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_EACH
    )

    section = models.CharField(
        max_length=20,
        choices=SECTION_CHOICES,
        default=SECTION_ALL
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_VEGETABLES
    )

    discount_percent = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        if self.discount_percent and self.discount_percent > 0:
            return self.price * (100 - self.discount_percent) / 100
        return self.price

    @property
    def availability_label(self):
        if self.stock > 0:
            if self.section == self.SECTION_SEASONAL:
                return "In Season"
            return "Available"
        return "Out of Stock"

    @property
    def unit_display(self):
        if self.unit == self.UNIT_EACH:
            return "each"

        if self.unit_value == self.unit_value.to_integral_value():
            clean_value = int(self.unit_value)
        else:
            clean_value = self.unit_value

        if self.unit == self.UNIT_PACK:
            return f"pack of {clean_value}"

        return f"{clean_value} {self.unit}"

    @property
    def price_display(self):
        return f"£{self.price} per {self.unit_display}"