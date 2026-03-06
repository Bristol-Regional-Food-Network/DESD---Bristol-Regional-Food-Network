from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from users.views import register
from core.auth_views import post_login_redirect
from products import views as product_api_views
from producers import views as producer_api_views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("core.urls")),

    # Auth (Philip backend)
    path("register/", register, name="register"),
    path("login/", auth_views.LoginView.as_view(
        template_name="auth/login.html",
        redirect_authenticated_user=True
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Post-login redirect
    path("post-login/", post_login_redirect, name="post_login_redirect"),

    # If you have these apps:
    path("products/", include("products.urls")),
    path("producer/", include("producers.urls")),
    path("customer/", include("customers.urls")),
    
    # API
    path("api/products/", product_api_views.api_product_collection, name="api_products_collection"),
    path("api/products/<int:product_id>/", product_api_views.api_product_resource, name="api_product_resource"),
    path("api/producers/", producer_api_views.api_producer_collection, name="api_producers_collection"),
    path("api/producers/<int:producer_id>/", producer_api_views.api_producer_resource, name="api_producer_resource"),
]

