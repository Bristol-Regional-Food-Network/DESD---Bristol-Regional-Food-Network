from decimal import Decimal
from django.db import models
from django.utils import timezone
from producers.models import Producer


class Product(models.Model):
    SECTION_ALL = "all"
    SECTION_SEASONAL = "seasonal"
    SECTION_DISCOUNTED = "discounted"
    SECTION_SURPLUS = "surplus"

    SECTION_CHOICES = [
        (SECTION_SEASONAL, "Seasonal Items"),
        (SECTION_DISCOUNTED, "Discounted Items"),
        (SECTION_SURPLUS, "Surplus Deals"),
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

    AVAILABILITY_SEASONAL = "seasonal"
    AVAILABILITY_YEAR_ROUND = "year_round"
    AVAILABILITY_UNAVAILABLE = "unavailable"

    AVAILABILITY_CHOICES = [
        (AVAILABILITY_SEASONAL, "Seasonal"),
        (AVAILABILITY_YEAR_ROUND, "Available Year-Round"),
        (AVAILABILITY_UNAVAILABLE, "Unavailable"),
    ]

    MONTH_CHOICES = [
        (1, "January"),
        (2, "February"),
        (3, "March"),
        (4, "April"),
        (5, "May"),
        (6, "June"),
        (7, "July"),
        (8, "August"),
        (9, "September"),
        (10, "October"),
        (11, "November"),
        (12, "December"),
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

    availability_mode = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default=AVAILABILITY_YEAR_ROUND,
    )
    season_start_month = models.PositiveSmallIntegerField(
        choices=MONTH_CHOICES,
        null=True,
        blank=True,
    )
    season_end_month = models.PositiveSmallIntegerField(
        choices=MONTH_CHOICES,
        null=True,
        blank=True,
    )

    best_before_date = models.DateField(null=True, blank=True)

    is_surplus = models.BooleanField(default=False)
    surplus_discount_percent = models.PositiveIntegerField(default=0)
    surplus_note = models.TextField(blank=True)
    surplus_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        if self.discount_percent and self.discount_percent > 0:
            return self.price * (100 - self.discount_percent) / 100
        return self.price

    @property
    def current_month(self):
        return timezone.localdate().month

    def is_in_season(self, month=None):
        if self.availability_mode != self.AVAILABILITY_SEASONAL:
            return False

        if not self.season_start_month or not self.season_end_month:
            return False

        month = month or self.current_month

        if self.season_start_month <= self.season_end_month:
            return self.season_start_month <= month <= self.season_end_month

        return month >= self.season_start_month or month <= self.season_end_month

    @property
    def season_range_display(self):
        if self.availability_mode != self.AVAILABILITY_SEASONAL:
            return ""
        if not self.season_start_month or not self.season_end_month:
            return ""
        start = dict(self.MONTH_CHOICES).get(self.season_start_month)
        end = dict(self.MONTH_CHOICES).get(self.season_end_month)
        return f"{start} - {end}"

    @property
    def is_surplus_active(self):
        if not self.is_surplus:
            return False
        if self.surplus_discount_percent < 10 or self.surplus_discount_percent > 50:
            return False
        if not self.surplus_expires_at:
            return False
        return timezone.now() < self.surplus_expires_at

    @property
    def active_price(self):
        if self.is_surplus_active:
            return self.price * (100 - self.surplus_discount_percent) / 100
        if self.discount_percent and self.discount_percent > 0:
            return self.discounted_price
        return self.price

    @property
    def customer_status(self):
        if self.stock <= 0:
            return "Out of Stock"

        if self.availability_mode == self.AVAILABILITY_UNAVAILABLE:
            return "Unavailable"

        if self.availability_mode == self.AVAILABILITY_YEAR_ROUND:
            return "Available Year-Round"

        if self.availability_mode == self.AVAILABILITY_SEASONAL:
            return "In Season" if self.is_in_season() else "Out of Season"

        return "Unavailable"

    @property
    def is_visible_to_customers(self):
        if self.stock <= 0:
            return False

        if self.availability_mode == self.AVAILABILITY_UNAVAILABLE:
            return False

        if self.availability_mode == self.AVAILABILITY_YEAR_ROUND:
            return True

        if self.availability_mode == self.AVAILABILITY_SEASONAL:
            return self.is_in_season()

        return False

    @property
    def season_starts_next_month(self):
        if self.availability_mode != self.AVAILABILITY_SEASONAL:
            return False
        if not self.season_start_month:
            return False

        next_month = 1 if self.current_month == 12 else self.current_month + 1
        return self.season_start_month == next_month

    @property
    def surplus_time_remaining(self):
        if not self.is_surplus_active:
            return ""
        delta = self.surplus_expires_at - timezone.now()
        total_hours = int(delta.total_seconds() // 3600)
        if total_hours < 24:
            return f"{total_hours} hours left"
        days = total_hours // 24
        hours = total_hours % 24
        if hours == 0:
            return f"{days} day(s) left"
        return f"{days} day(s), {hours} hour(s) left"

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