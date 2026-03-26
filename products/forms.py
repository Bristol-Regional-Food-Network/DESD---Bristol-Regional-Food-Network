from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    surplus_duration_hours = forms.IntegerField(
        required=False,
        min_value=1,
        label="Surplus Deal Duration (hours)",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"})
    )

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
            "availability_mode",
            "season_start_month",
            "season_end_month",
            "best_before_date",
            "is_surplus",
            "surplus_discount_percent",
            "surplus_note",
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
            "availability_mode": forms.Select(attrs={"class": "form-select"}),
            "season_start_month": forms.Select(attrs={"class": "form-select"}),
            "season_end_month": forms.Select(attrs={"class": "form-select"}),
            "best_before_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_surplus": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "surplus_discount_percent": forms.NumberInput(attrs={"class": "form-control", "min": "10", "max": "50"}),
            "surplus_note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
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

    def clean_stock(self):
        stock = self.cleaned_data.get("stock", 0)
        if stock < 0:
            raise forms.ValidationError("Stock cannot be negative.")
        return stock

    def clean(self):
        cleaned_data = super().clean()

        availability_mode = cleaned_data.get("availability_mode")
        season_start_month = cleaned_data.get("season_start_month")
        season_end_month = cleaned_data.get("season_end_month")
        is_surplus = cleaned_data.get("is_surplus")
        surplus_discount_percent = cleaned_data.get("surplus_discount_percent", 0)
        surplus_duration_hours = cleaned_data.get("surplus_duration_hours")

        if availability_mode == Product.AVAILABILITY_SEASONAL:
            if not season_start_month or not season_end_month:
                raise forms.ValidationError(
                    "Please choose both a season start month and season end month for seasonal products."
                )
        else:
            cleaned_data["season_start_month"] = None
            cleaned_data["season_end_month"] = None

        if is_surplus:
            if surplus_discount_percent < 10 or surplus_discount_percent > 50:
                raise forms.ValidationError("Surplus discount must be between 10% and 50%.")
            if not surplus_duration_hours:
                raise forms.ValidationError("Please provide a surplus deal duration in hours.")
        else:
            cleaned_data["surplus_discount_percent"] = 0
            cleaned_data["surplus_note"] = ""

        return cleaned_data