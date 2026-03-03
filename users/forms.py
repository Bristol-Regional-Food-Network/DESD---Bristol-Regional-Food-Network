from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

# Registration form extends the built-in User model
class RegistrationForm(forms.ModelForm):
    # Add a password field to the form that uses a password input widget for secure entry
    password = forms.CharField(widget=forms.PasswordInput)
    # Add a choice field for the user role based on the roles defined in the UserProfile model
    role = forms.ChoiceField(choices=UserProfile.roles)

    # Meta class for the model and fields in the form
    class Meta:
        model = User
        fields = ['username', 'email', 'password']