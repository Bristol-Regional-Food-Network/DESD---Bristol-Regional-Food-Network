from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


COMMISSION_RATE_DEFAULT = Decimal("0.0500")  # 5%


class Producer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    postcode = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["postcode"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class Customer(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, blank=True)
    postcode = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["postcode"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.full_name


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, default="each")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    harvest_date = models.DateField(null=True, blank=True)
    best_before_date = models.DateField(null=True, blank=True)
    is_organic = models.BooleanField(default=False)
    allergen_info = models.TextField(blank=True)
    origin_notes = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["producer"]),
            models.Index(fields=["category"]),
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]
        unique_together = [("producer", "name")]
        constraints = [
            models.CheckConstraint(check=Q(price__gte=0), name="product_price_nonnegative"),
        ]

    def __str__(self):
        return self.name


class Inventory(models.Model):
    """
    Inventory + availability window.
    """
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)
    stock_qty = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(stock_qty__gte=0), name="inventory_stock_nonnegative"),
            models.CheckConstraint(
                check=Q(available_from__isnull=True) | Q(available_to__isnull=True) | Q(available_to__gte=models.F("available_from")),
                name="inventory_valid_availability_range",
            ),
        ]

    def clean(self):
        if self.available_from and self.available_to and self.available_to < self.available_from:
            raise ValidationError("available_to must be on/after available_from.")

    def __str__(self):
        return f"Inventory for {self.product.name}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FULFILLED = "fulfilled", "Fulfilled"
        CANCELLED = "cancelled", "Cancelled"

    class Fulfilment(models.TextChoices):
        COLLECTION = "collection", "Collection"
        DELIVERY = "delivery", "Delivery"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    fulfilment_method = models.CharField(max_length=20, choices=Fulfilment.choices, default=Fulfilment.COLLECTION)
    delivery_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional stored totals (nice for admin / reporting). Kept consistent via recalculate_totals().
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def recalculate_totals(self, save: bool = True) -> None:
        subtotal = Decimal("0.00")
        for item in self.items.all():
            subtotal += item.line_total

        commission = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))
        total = subtotal  # customer pays subtotal; commission deducted from producer settlements

        self.subtotal_amount = subtotal
        self.commission_amount = commission
        self.total_amount = total

        if save:
            self.save(update_fields=["subtotal_amount", "commission_amount", "total_amount"])

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="order_items")

    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price_at_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        blank=True,
        null=True,
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        default=Decimal("0.00"),
    )

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["producer"]),
            models.Index(fields=["product"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(quantity__gte=1), name="orderitem_quantity_positive"),
            models.CheckConstraint(check=Q(line_total__gte=0), name="orderitem_line_total_nonnegative"),
        ]

    def clean(self):
        # Ensure producer matches the product's producer (data integrity)
        if self.product_id and self.producer_id and self.product.producer_id != self.producer_id:
            raise ValidationError("producer must match product.producer.")

    def save(self, *args, **kwargs):
        # Default producer from product if not set
        if self.product_id and not self.producer_id:
            self.producer = self.product.producer

        # Default unit price from product if not set
        if self.product_id and (self.unit_price_at_purchase is None):
            self.unit_price_at_purchase = self.product.price

        self.line_total = (Decimal(self.quantity) * Decimal(self.unit_price_at_purchase)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

        # Keep parent totals consistent
        if self.order_id:
            self.order.recalculate_totals(save=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order_id})"


class Payment(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=50, default="test")
    provider_ref = models.CharField(max_length=255, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    currency = models.CharField(max_length=10, default="GBP")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["paid_at"]),
        ]

    def __str__(self):
        return f"Payment(Order #{self.order_id}, {self.status})"


class PayoutBatch(models.Model):
    week_start = models.DateField()
    week_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["week_start", "week_end"], name="uniq_payout_batch_period"),
            models.CheckConstraint(check=Q(week_end__gte=models.F("week_start")), name="payoutbatch_valid_range"),
        ]

    def __str__(self):
        return f"PayoutBatch({self.week_start} → {self.week_end})"


class ProducerPayout(models.Model):
    """
    Weekly settlement per producer.
    Totals are kept consistent by calling recalculate() (we also call it from ProducerPayoutLine.save()).
    """
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        EXPORTED = "exported", "Exported"
        PAID = "paid", "Paid"

    batch = models.ForeignKey(PayoutBatch, on_delete=models.CASCADE, related_name="payouts")
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="payouts")

    gross_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    commission_rate = models.DecimalField(max_digits=6, decimal_places=4, default=COMMISSION_RATE_DEFAULT)  # store for audit
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "producer"], name="uniq_producer_payout_per_batch"),
            models.CheckConstraint(check=Q(commission_rate__gte=0), name="producerpayout_commission_rate_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["producer"]),
            models.Index(fields=["status"]),
        ]

    def recalculate(self, save: bool = True) -> None:
        gross = Decimal("0.00")
        for line in self.lines.all():
            gross += line.gross_amount

        commission = (gross * Decimal(self.commission_rate)).quantize(Decimal("0.01"))
        net = (gross - commission).quantize(Decimal("0.01"))

        self.gross_sales = gross
        self.commission_amount = commission
        self.net_payable = net

        if save:
            self.save(update_fields=["gross_sales", "commission_amount", "net_payable"])

    def __str__(self):
        return f"ProducerPayout({self.producer.name}, {self.batch})"


class ProducerPayoutLine(models.Model):
    producer_payout = models.ForeignKey(ProducerPayout, on_delete=models.CASCADE, related_name="lines")
    order_item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name="payout_line")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    def save(self, *args, **kwargs):
        # Default gross_amount to the order item line total if not provided
        if self.order_item_id and (self.gross_amount is None):
            self.gross_amount = self.order_item.line_total

        super().save(*args, **kwargs)

        # Keep payout header totals consistent
        if self.producer_payout_id:
            self.producer_payout.recalculate(save=True)

    def __str__(self):
        return f"PayoutLine(Item #{self.order_item_id})"


class PostcodeDistance(models.Model):
    from_postcode = models.CharField(max_length=20)
    to_postcode = models.CharField(max_length=20)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["from_postcode", "to_postcode"], name="uniq_postcode_pair"),
            models.CheckConstraint(check=Q(distance_km__gte=0), name="postcodedistance_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["from_postcode", "to_postcode"]),
        ]

    def __str__(self):
        return f"{self.from_postcode} → {self.to_postcode} ({self.distance_km} km)"


class SurplusOffer(models.Model):
    """
    Time-bounded last-minute discount for waste reduction.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="surplus_offers")
    discount_percent = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    note = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["starts_at", "ends_at"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(discount_percent__gte=0) & Q(discount_percent__lte=100), name="surplus_discount_percent_range"),
            models.CheckConstraint(check=Q(ends_at__gt=models.F("starts_at")), name="surplus_valid_time_window"),
        ]

    def clean(self):
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be after starts_at.")

    def __str__(self):
        return f"SurplusOffer({self.product.name}, {self.discount_percent}%)"


class ContentPost(models.Model):
    class PostType(models.TextChoices):
        RECIPE = "recipe", "Recipe"
        STORAGE = "storage", "Storage"
        FARM_STORY = "farm_story", "Farm story"
        OTHER = "other", "Other"

    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name="content_posts")
    post_type = models.CharField(max_length=20, choices=PostType.choices, default=PostType.OTHER)
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["producer"]),
            models.Index(fields=["post_type"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.post_type})"