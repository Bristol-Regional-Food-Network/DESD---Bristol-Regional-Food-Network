from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    # Producer content management
    path('', views.content_dashboard, name='content_dashboard'),
    path('recipes/add/', views.add_recipe, name='add_recipe'),
    path('recipes/<int:recipe_id>/edit/', views.edit_recipe, name='edit_recipe'),
    path('recipes/<int:recipe_id>/delete/', views.delete_recipe, name='delete_recipe'),
    path('stories/add/', views.add_story, name='add_story'),
    path('stories/<int:story_id>/edit/', views.edit_story, name='edit_story'),
    path('stories/<int:story_id>/delete/', views.delete_story, name='delete_story'),

    # Public / customer views
    path('recipes/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('producers/<int:producer_id>/', views.producer_stories, name='producer_content'),
    path('recipes/<int:recipe_id>/save/', views.save_recipe, name='save_recipe'),
    path('recipes/<int:recipe_id>/unsave/', views.unsave_recipe, name='unsave_recipe'),
    path('saved/', views.saved_recipes, name='saved_recipes'),
]
