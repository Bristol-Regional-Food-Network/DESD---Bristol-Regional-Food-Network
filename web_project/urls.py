from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from users.views import register, customer_register, producer_register, community_group_register, restaurant_register, employee_register, pending_employees, approve_employee

from core.auth_views import post_login_redirect

from products import views as product_api_views
from producers import views as producer_api_views
from ai_engineer import views as views_ai

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("core.urls")),

    # Auth
    path("register/", register, name="register"),
    path("register/customer/", customer_register, name="customer_register"),
    path("register/producer/", producer_register, name="producer_register"),
    path("register/community-group/", community_group_register, name="community_group_register"),
    path("register/restaurant/", restaurant_register, name="restaurant_register"),
    path("register/employee/", employee_register, name="employee_register"),

    path("employees/pending/", pending_employees, name="pending_employees"),
    path("employees/<int:profile_id>/approve/", approve_employee, name="approve_employee"),

    # Login/logout paths
    path("login/", auth_views.LoginView.as_view(
        template_name="auth/login.html",
        redirect_authenticated_user=True
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Post-login redirect
    path("post-login/", post_login_redirect, name="post_login_redirect"),

    # Apps
    path("products/", include("products.urls")),
    path("producer/", include("producers.urls")),
    path("customer/", include("customers.urls")),
    path("manager/", include("managers.urls")),
    path("basket/", include("basket.urls")),
    path("ai-engineer/", include("ai_engineer.urls")),
    path("content/", include("content.urls")),

    # API
    path("api/products/", product_api_views.api_product_collection, name="api_products_collection"),
    path("api/products/<int:product_id>/", product_api_views.api_product_resource, name="api_product_resource"),
    path("api/producers/", producer_api_views.api_producer_collection, name="api_producers_collection"),
    path("api/producers/<int:producer_id>/", producer_api_views.api_producer_resource, name="api_producer_resource"),
    path("recommendations/", views_ai.customer_recommendations, name="customer_recommendations"),
    path("api/recommendations/", views_ai.recommendations_api, name="recommendations_api"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)