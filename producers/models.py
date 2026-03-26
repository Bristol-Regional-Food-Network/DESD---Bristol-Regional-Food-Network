from django.db import models
from django.contrib.auth.models import User


class Producer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="producer")
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    postcode = models.CharField(max_length=12, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return self.display_name