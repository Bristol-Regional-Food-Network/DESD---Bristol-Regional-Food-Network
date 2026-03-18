from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock", "section", "discount_percent"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "section": forms.Select(attrs={"class": "form-select"}),
            "discount_percent": forms.NumberInput(attrs={"class": "form-control", "min": "0", "max": "100"}),
        }

    def clean_discount_percent(self):
        discount = self.cleaned_data.get("discount_percent", 0)
        if discount < 0 or discount > 100:
            raise forms.ValidationError("Discount percent must be between 0 and 100.")
        return discount