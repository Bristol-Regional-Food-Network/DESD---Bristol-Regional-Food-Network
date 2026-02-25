from django.db import models
from producers.models import Producer

class Product(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    available_from = models.DateField()
    available_to = models.DateField()

    def __str__(self):
        return self.name