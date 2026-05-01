from datetime import datetime
from django import forms


class PaymentForm(forms.Form):
    cardholder_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Full name on card",
        })
    )

    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "1234 5678 9012 3456",
            "maxlength": "19",
        })
    )

    expiry_month = forms.IntegerField(
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "MM",
            "min": "1",
            "max": "12",
        })
    )

    expiry_year = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "YY",
            "min": "0",
            "max": "99",
        })
    )

    cvv = forms.CharField(
        min_length=3,
        max_length=4,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "123",
            "maxlength": "4",
        })
    )

    billing_address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Street address",
        })
    )

    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    postcode = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    country = forms.CharField(
        max_length=100,
        initial="UK",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    def clean_card_number(self):
        card_number = self.cleaned_data["card_number"].replace(" ", "")
        if not card_number.isdigit():
            raise forms.ValidationError("Card number must contain digits only.")
        if len(card_number) != 16:
            raise forms.ValidationError("Card number must be 16 digits.")
        return card_number

    def clean_cvv(self):
        cvv = self.cleaned_data["cvv"]
        if not cvv.isdigit():
            raise forms.ValidationError("CVV must contain digits only.")
        if len(cvv) not in [3, 4]:
            raise forms.ValidationError("CVV must be 3 or 4 digits.")
        return cvv

    def clean_expiry_year(self):
        year = self.cleaned_data["expiry_year"]
        if year < 0 or year > 99:
            raise forms.ValidationError("Enter a valid 2-digit year.")
        return year

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get("expiry_month")
        year = cleaned_data.get("expiry_year")

        if month is not None and year is not None:
            now = datetime.now()
            current_year = now.year % 100
            current_month = now.month

            if year < current_year:
                raise forms.ValidationError("Card has expired.")
            if year == current_year and month < current_month:
                raise forms.ValidationError("Card has expired.")

        return cleaned_data