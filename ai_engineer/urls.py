from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.ai_engineer_dashboard, name="ai_engineer_dashboard"),
    path("train/", views.train_model, name="ai_engineer_train"),
    path("recommendations/", views.view_recommendations, name="ai_engineer_recommendations"),
    path("customer-recommendations/", views.customer_recommendations, name="customer_recommendations"),
    path("api/recommendations/", views.recommendations_api, name="recommendations_api"),
]