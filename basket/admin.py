from django.contrib import admin
from .models import Order, OrderItem, ProducerOrder, OrderStatusHistory, RecurringOrder, RecurringOrderItem


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
        return obj.subtotal if obj.pk else 0
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
        return obj.subtotal if obj.pk else 0
    subtotal.short_description = "Subtotal"


class RecurringOrderItemInline(admin.TabularInline):
    model = RecurringOrderItem
    extra = 0




@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "order_item", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("old_status", "new_status", "created_at")
    search_fields = ("order__id", "order_item__product_name", "note", "changed_by__username")
    readonly_fields = ("created_at",)


@admin.register(RecurringOrder)
class RecurringOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "user",
        "frequency",
        "order_day",
        "delivery_day",
        "next_run_date",
        "status",
    )
    list_filter = ("status", "frequency", "order_day", "delivery_day")
    search_fields = ("name", "user__username", "cardholder_name")
    inlines = [RecurringOrderItemInline]


@admin.register(RecurringOrderItem)
class RecurringOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recurring_order",
        "product_name",
        "producer_name",
        "quantity",
        "next_quantity_override",
    )
    search_fields = ("product_name", "producer_name", "recurring_order__id")