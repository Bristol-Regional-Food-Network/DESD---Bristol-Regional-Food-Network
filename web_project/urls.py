"""
URL configuration for web_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from users.views import register
from users.views import producer_test_page, customer_test_page
from .views import home



urlpatterns = [
    # Home page URL that maps to the home view
    path('', home, name='home'),
    
    # Admin site URL
    path('admin/', admin.site.urls),

    # URL patterns for user registration, login, and logout
    path('register/', register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Test pages for producers and customers that require specific roles to access
    path('producer-test/', producer_test_page, name='producer-test'),
    path('customer-test/', customer_test_page, name='customer-test'),

]
