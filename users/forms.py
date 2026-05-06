# users/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class BaseRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})


class CustomerRegistrationForm(BaseRegistrationForm):
    address = forms.CharField(required=True, label="Address")
    postcode = forms.CharField(required=True, label="Postcode")

    class Meta:
        model = User
        fields = ["username", "email", "password", "address", "postcode"]


class ProducerRegistrationForm(BaseRegistrationForm):
    address = forms.CharField(required=True, label="Business Address")
    postcode = forms.CharField(required=True, label="Business Postcode")
    farm_name = forms.CharField(required=True, label="Farm Name")

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "address",
            "postcode",
            "farm_name",
        ]


class CommunityGroupRegistrationForm(BaseRegistrationForm):
    organisation_name = forms.CharField(required=True, label="Organisation Name")
    organisation_type = forms.ChoiceField(
        required=True,
        label="Organisation Type",
        choices=[
            ("school", "School"),
            ("charity", "Charity"),
            ("community_group", "Community Group"),
            ("other", "Other"),
        ],
    )
    contact_name = forms.CharField(required=True, label="Contact Name")
    address = forms.CharField(required=True, label="Organisation Address")
    postcode = forms.CharField(required=True, label="Postcode")

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "organisation_name",
            "organisation_type",
            "contact_name",
            "address",
            "postcode",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisation_type"].widget.attrs.update({"class": "form-select"})


class RestaurantRegistrationForm(BaseRegistrationForm):
    business_name = forms.CharField(required=True, label="Restaurant / Business Name")
    contact_name = forms.CharField(required=True, label="Contact Name")
    address = forms.CharField(required=True, label="Business Address")
    postcode = forms.CharField(required=True, label="Business Postcode")

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "business_name",
            "contact_name",
            "address",
            "postcode",
        ]


class EmployeeRegistrationForm(BaseRegistrationForm):
    role = forms.ChoiceField(
        choices=[
            ("ai_engineer", "AI Engineer"),
            ("manager", "Manager"),
        ],
        label="Register as"
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].widget.attrs.update({"class": "form-select"})