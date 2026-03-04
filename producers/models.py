from django.db import models
from django.contrib.auth.models import User

class Producer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    farm_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.farm_name