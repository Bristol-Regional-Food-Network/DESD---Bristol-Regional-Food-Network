from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "producer",
        "price",
        "unit_value",
        "unit",
        "stock",
        "category",
        "section",
        "discount_percent",
    )
    list_filter = (
        "category",
        "section",
        "unit",
        "producer",
    )
    search_fields = (
        "name",
        "description",
        "producer__display_name",
    )
    ordering = ("name",)