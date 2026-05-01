# users/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    role = forms.ChoiceField(choices=UserProfile.roles, label="Register as")

    address = forms.CharField(required=False, label="Address")
    postcode = forms.CharField(required=False, label="Postcode")
    farm_name = forms.CharField(required=False, label="Farm Name")


    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})
        self.fields["role"].widget.attrs.update({"class": "form-select"})

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")

        if role in ["customer", "producer"]:
            if not cleaned_data.get("address"):
                self.add_error("address", "Address is required")
            if not cleaned_data.get("postcode"):
                self.add_error("postcode", "Postcode is required")

        if role == "producer":
            if not cleaned_data.get("farm_name"):
                self.add_error("farm_name", "Farm name is required")
