from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("producers", "__first__"),
        ("products", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("paid", "Paid"), ("cancelled", "Cancelled"), ("fulfilled", "Fulfilled")], default="paid", max_length=20)),
                ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orders", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=8)),
                ("fulfilment_status", models.CharField(choices=[("pending", "Pending"), ("fulfilled", "Fulfilled"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="basket.order")),
                ("producer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="producers.producer")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="products.product")),
            ],
        ),
    ]
