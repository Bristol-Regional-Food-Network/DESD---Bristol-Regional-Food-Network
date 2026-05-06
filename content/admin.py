from django.contrib import admin
from .models import Recipe, FarmStory, SavedRecipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'producer', 'seasonal_tag', 'is_published', 'created_at')
    list_filter = ('is_published', 'seasonal_tag')
    search_fields = ('title', 'producer__display_name')
    filter_horizontal = ('linked_products',)


@admin.register(FarmStory)
class FarmStoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'producer', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'producer__display_name')


@admin.register(SavedRecipe)
class SavedRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'saved_at')
