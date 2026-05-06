from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('basket', '0005_alter_orderitem_price'),
        ('producers', '0004_producer_latitude_producer_longitude'),
        ('products', '0010_product_ai_action_product_ai_colour_score_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Weekly order', max_length=120)),
                ('frequency', models.CharField(
                    choices=[('weekly', 'Every week'), ('fortnightly', 'Every two weeks')],
                    default='weekly',
                    max_length=20,
                )),
                ('order_day', models.IntegerField(
                    choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
                             (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')],
                    default=0,
                )),
                ('delivery_day', models.IntegerField(
                    choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
                             (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')],
                    default=2,
                )),
                ('cardholder_name', models.CharField(max_length=100)),
                ('card_last4', models.CharField(max_length=4)),
                ('billing_address', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=100)),
                ('postcode', models.CharField(max_length=20)),
                ('country', models.CharField(default='UK', max_length=100)),
                ('next_run_date', models.DateField()),
                ('next_delivery_date', models.DateField()),
                ('status', models.CharField(
                    choices=[('active', 'Active'), ('paused', 'Paused'), ('cancelled', 'Cancelled')],
                    default='active',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='recurring_orders',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='RecurringOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=200)),
                ('producer_name', models.CharField(blank=True, max_length=120)),
                ('unit_display', models.CharField(default='each', max_length=50)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('next_quantity_override', models.PositiveIntegerField(blank=True, null=True)),
                ('producer', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='producers.producer',
                )),
                ('product', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='products.product',
                )),
                ('recurring_order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='basket.recurringorder',
                )),
            ],
        ),
    ]
