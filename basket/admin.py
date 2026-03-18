from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "cardholder_name", "card_last4", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at", "country")
    search_fields = ("cardholder_name", "postcode", "city")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product_name", "price", "quantity")
    search_fields = ("product_name",)