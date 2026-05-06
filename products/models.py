from decimal import Decimal
from django.db import models
from django.utils import timezone
from producers.models import Producer
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Avg


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
    allergen_info = models.TextField(
        default="No common allergens listed",
        help_text="Clearly list allergens such as milk, eggs, nuts, gluten, or state that no common allergens are listed."
    )
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_organic = models.BooleanField(default=False)

    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Send alert when stock falls below this number"
    )

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

    # Image field for AI quality assessment
    image = models.ImageField(upload_to="products/", null=True, blank=True)

    # AI Quality Assessment Fields
    ai_predicted_label = models.CharField(max_length=20, blank=True)
    ai_fresh_probability = models.FloatField(null=True, blank=True)
    ai_rotten_probability = models.FloatField(null=True, blank=True)

    ai_colour_score = models.FloatField(null=True, blank=True)
    ai_size_score = models.FloatField(null=True, blank=True)
    ai_ripeness_score = models.FloatField(null=True, blank=True)

    ai_grade = models.CharField(max_length=2, blank=True)
    ai_action = models.CharField(max_length=100, blank=True)
    ai_explanation = models.TextField(blank=True)

    # Timestamp for when AI assessment was last performed
    ai_last_checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def allergen_display(self):
        value = (self.allergen_info or "").strip()
        return value or "No common allergens listed"

    @property
    def has_allergen_warning(self):
        value = self.allergen_display.lower()
        no_allergen_phrases = [
            "no common allergens listed",
            "no common allergens",
            "none",
            "n/a",
        ]
        return not any(value == phrase or value.startswith(f"{phrase}.") for phrase in no_allergen_phrases)

    @property
    def discounted_price(self):
        try:
            dp = int(self.discount_percent or 0)
        except Exception:
            dp = 0
        if dp > 0:
            return self.price * (100 - dp) / 100
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
        try:
            sdp = int(self.surplus_discount_percent or 0)
        except Exception:
            sdp = 0
        if self.is_surplus_active and sdp > 0:
            return self.price * (100 - sdp) / 100
        try:
            dp = int(self.discount_percent or 0)
        except Exception:
            dp = 0
        if dp > 0:
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

    @property
    def average_rating(self):
        result = self.reviews.filter(is_approved=True).aggregate(avg=Avg("rating"))
        return result["avg"] or 0

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    def get_ai_grade_badge_class(self):
        if self.ai_grade == "A":
            return "bg-success"
        elif self.ai_grade == "B":
            return "bg-warning text-dark"
        elif self.ai_grade == "C":
            return "bg-danger"
        return "bg-secondary"


class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_reviews"
    )
    order = models.ForeignKey(
        "basket.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=120)
    review_text = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=True)

    is_approved = models.BooleanField(default=True)
    producer_reply = models.TextField(blank=True)
    producer_replied_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "customer"],
                name="unique_review_per_customer_per_product"
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.customer.username} ({self.rating}/5)"


class StockAlert(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_alerts"
    )
    current_stock = models.PositiveIntegerField()
    threshold = models.PositiveIntegerField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "Resolved" if self.is_resolved else "Active"
        return f"Low Stock Alert: {self.product.name} - {self.current_stock} remaining [{status}]"