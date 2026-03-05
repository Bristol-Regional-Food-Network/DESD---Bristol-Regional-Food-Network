from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from users.views import register
from core.auth_views import post_login_redirect

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

]