from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "producer",
        "price",
        "stock",
        "section",
        "discount_percent",
        "availability_mode",
        "is_surplus",
        "surplus_discount_percent",
        "surplus_expires_at",
    )
    list_filter = (
        "section",
        "availability_mode",
        "is_surplus",
        "producer",
    )
    search_fields = (
        "name",
        "description",
        "producer__farm_name",
        "producer__display_name",
        "surplus_note",
    )