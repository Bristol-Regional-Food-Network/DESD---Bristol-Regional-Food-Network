from django.db import models
from django.utils import timezone
from producers.models import Producer
from products.models import Product


class Recipe(models.Model):
    SEASON_CHOICES = [
        ('spring', 'Spring'),
        ('summer', 'Summer'),
        ('autumn_winter', 'Autumn/Winter'),
        ('year_round', 'Year Round'),
    ]

    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name='recipes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    ingredients = models.TextField(help_text="Enter each ingredient on a new line")
    instructions = models.TextField()
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)
    linked_products = models.ManyToManyField(Product, blank=True, related_name='recipes')
    seasonal_tag = models.CharField(max_length=20, choices=SEASON_CHOICES, default='year_round')
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def ingredients_list(self):
        return [line.strip() for line in self.ingredients.splitlines() if line.strip()]

    @property
    def instructions_list(self):
        return [line.strip() for line in self.instructions.splitlines() if line.strip()]


class FarmStory(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name='farm_stories')
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='farm_stories/', null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Farm Story'
        verbose_name_plural = 'Farm Stories'

    def __str__(self):
        return self.title


class SavedRecipe(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='saved_recipes')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')

    def __str__(self):
        return f"{self.user.username} saved {self.recipe.title}"
