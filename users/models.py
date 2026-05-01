from django.db import models
from django.contrib.auth.models import User

# Simple user profile model to extend the built-in User model with a role field
class UserProfile(models.Model):
    # Define user roles as choices for the role field
    roles = [
        ('customer', 'Customer'),
        ('producer', 'Producer'),
        ('ai_engineer', 'AI Engineer'),
        ('manager', 'Manager'),
    ]
    # One-to-one with the built-in User model to link user profiles to users
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=roles)

    address = models.CharField(max_length=255, null=True, blank=True)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    farm_name = models.CharField(max_length=255, null=True, blank=True)

    def is_manager(self):
        return self.role == "manager"

    def can_access_customer(self):
        return self.role in ["customer", "manager"]

    def can_access_producer(self):
        return self.role in ["producer", "manager"]


    # String representation of class for printing user profiles
    def __str__(self):
        return f"{self.user.username} ({self.role})"