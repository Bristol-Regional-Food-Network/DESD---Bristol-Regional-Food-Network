from django.contrib import admin
from .models import Order, OrderItem, ProducerOrder


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product",
        "product_name",
        "producer_name",
        "unit_display",
        "price",
        "quantity",
        "subtotal",
        "producer_order",
    )
    can_delete = False

    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = "Subtotal"


class ProducerOrderInline(admin.TabularInline):
    model = ProducerOrder
    extra = 0
    readonly_fields = (
        "producer_name",
        "delivery_date",
        "subtotal_amount",
        "payout_amount",
        "status",
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "producer_name",
        "total_amount",
        "commission_amount",
        "producer_amount",
        "delivery_date",
        "payment_reference",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "country",
        "delivery_date",
        "created_at",
    )
    search_fields = (
        "id",
        "user__username",
        "user__email",
        "cardholder_name",
        "producer_name",
        "payment_reference",
        "postcode",
    )
    readonly_fields = (
        "created_at",
        "payment_reference",
        "card_last4",
        "total_amount",
        "commission_amount",
        "producer_amount",
    )
    inlines = [ProducerOrderInline, OrderItemInline]

    fieldsets = (
        ("Order Overview", {
            "fields": (
                "user",
                "status",
                "producer_name",
                "payment_reference",
                "created_at",
            )
        }),
        ("Amounts", {
            "fields": (
                "total_amount",
                "commission_amount",
                "producer_amount",
            )
        }),
        ("Customer Details", {
            "fields": (
                "cardholder_name",
                "card_last4",
                "billing_address",
                "city",
                "postcode",
                "country",
                "delivery_date",
            )
        }),
    )


@admin.register(ProducerOrder)
class ProducerOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "producer_name",
        "delivery_date",
        "subtotal_amount",
        "payout_amount",
        "status",
    )
    list_filter = (
        "status",
        "delivery_date",
        "producer_name",
    )
    search_fields = (
        "order__id",
        "producer_name",
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "producer_order",
        "product_name",
        "producer_name",
        "unit_display",
        "price",
        "quantity",
        "subtotal",
    )
    list_filter = ("producer_name",)
    search_fields = ("product_name", "producer_name", "order__id")

    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = "Subtotal"