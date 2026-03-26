from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("basket", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("paid", "Paid"),
                    ("partially_fulfilled", "Partially Fulfilled"),
                    ("cancelled", "Cancelled"),
                    ("fulfilled", "Fulfilled"),
                ],
                default="paid",
                max_length=20,
            ),
        ),
    ]
