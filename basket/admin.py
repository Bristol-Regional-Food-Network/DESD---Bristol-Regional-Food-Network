from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total_amount", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer__username",)
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "producer", "quantity", "unit_price")