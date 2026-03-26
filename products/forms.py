from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "price",
            "stock",
            "unit_value",
            "unit",
            "category",
            "section",
            "discount_percent",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "unit_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "section": forms.Select(attrs={"class": "form-select"}),
            "discount_percent": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100"}),
        }

    def clean_discount_percent(self):
        discount = self.cleaned_data.get("discount_percent", 0)
        if discount < 0 or discount > 100:
            raise forms.ValidationError("Discount percent must be between 0 and 100.")
        return discount

    def clean_unit_value(self):
        unit_value = self.cleaned_data.get("unit_value")
        if unit_value is None or unit_value <= 0:
            raise forms.ValidationError("Unit value must be greater than 0.")
        return unit_value