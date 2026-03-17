from django import forms
from django.contrib.auth.models import User
from producers.models import Producer
from basket.models import Order
from core.models import CustomerProfile, ProducerProfile


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]


class ProducerForm(forms.ModelForm):
    class Meta:
        model = Producer
        fields = ["display_name", "bio", "location", "phone", "website"]


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer", "total_amount", "status", "notes"]
