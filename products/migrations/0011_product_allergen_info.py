# Generated manually for TC-015 allergen information support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0010_product_ai_action_product_ai_colour_score_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="allergen_info",
            field=models.TextField(
                default="No common allergens listed",
                help_text="Clearly list allergens such as milk, eggs, nuts, gluten, or state that no common allergens are listed.",
            ),
        ),
    ]
