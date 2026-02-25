from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Producer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    postcode = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, blank=True)
    postcode = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, default="each")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

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

    def __str__(self):
        return self.name


class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)
    stock_qty = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Inventory for {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("fulfilled", "Fulfilled"),
        ("cancelled", "Cancelled"),
    ]
    FULFILMENT_CHOICES = [
        ("collection", "Collection"),
        ("delivery", "Delivery"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    fulfilment_method = models.CharField(max_length=20, choices=FULFILMENT_CHOICES, default="collection")
    delivery_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="order_items")

    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    line_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["producer"]),
            models.Index(fields=["product"]),
        ]

    def save(self, *args, **kwargs):
        if not self.producer_id:
            self.producer = self.product.producer
        self.line_total = (Decimal(self.quantity) * self.unit_price_at_purchase).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    provider = models.CharField(max_length=50, default="test")
    provider_ref = models.CharField(max_length=255, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    currency = models.CharField(max_length=10, default="GBP")
    status = models.CharField(max_length=20, default="unpaid")  # unpaid, paid, failed, refunded
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["paid_at"]),
        ]


class PayoutBatch(models.Model):
    week_start = models.DateField()
    week_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["week_start", "week_end"], name="uniq_payout_batch_period")
        ]


class ProducerPayout(models.Model):
    batch = models.ForeignKey(PayoutBatch, on_delete=models.CASCADE, related_name="payouts")
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT, related_name="payouts")

    gross_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    commission_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0500"))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=20, default="pending")  # pending, exported, paid
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "producer"], name="uniq_producer_payout_per_batch")
        ]
        indexes = [models.Index(fields=["producer"])]


class ProducerPayoutLine(models.Model):
    producer_payout = models.ForeignKey(ProducerPayout, on_delete=models.CASCADE, related_name="lines")
    order_item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name="payout_line")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])


class PostcodeDistance(models.Model):
    from_postcode = models.CharField(max_length=20)
    to_postcode = models.CharField(max_length=20)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["from_postcode", "to_postcode"], name="uniq_postcode_pair")
        ]


class SurplusOffer(models.Model):
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


class ContentPost(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name="content_posts")
    type = models.CharField(max_length=20)  # recipe, storage, farm_story
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["producer"]),
            models.Index(fields=["type"]),
            models.Index(fields=["is_published"]),
        ]