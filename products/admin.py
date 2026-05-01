from django.contrib import admin
from .models import Product, Review


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "producer",
        "category",
        "price",
        "stock",
        "availability_mode",
        "is_organic",
        "is_surplus",
    )
    list_filter = (
        "category",
        "availability_mode",
        "is_organic",
        "is_surplus",
        "section",
    )
    search_fields = ("name", "description", "producer__display_name")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "customer",
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    )
    list_filter = (
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    )
    search_fields = (
        "product__name",
        "customer__username",
        "title",
        "review_text",
    )