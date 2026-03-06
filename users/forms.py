# users/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    role = forms.ChoiceField(choices=UserProfile.roles, label="Register as")

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})
        self.fields["role"].widget.attrs.update({"class": "form-select"})