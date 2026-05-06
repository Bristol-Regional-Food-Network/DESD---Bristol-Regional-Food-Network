# Generated for community group and restaurant account support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_userprofile_admin_approved"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="business_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="contact_name",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="organisation_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="organisation_type",
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("customer", "Customer"),
                    ("producer", "Producer"),
                    ("ai_engineer", "AI Engineer"),
                    ("manager", "Manager"),
                    ("community_group", "Community Group"),
                    ("restaurant", "Restaurant"),
                ],
                max_length=20,
            ),
        ),
    ]
