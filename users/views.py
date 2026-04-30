from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from .forms import (
    CustomerRegistrationForm,
    ProducerRegistrationForm,
    EmployeeRegistrationForm,
)
from .models import UserProfile


def register(request):
    return render(request, "auth/register.html")


def customer_register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = "customer"
            profile.address = form.cleaned_data.get("address")
            profile.postcode = form.cleaned_data.get("postcode")
            profile.farm_name = ""
            profile.admin_approved = True
            profile.save()

            login(request, user)
            return redirect("/")
    else:
        form = CustomerRegistrationForm()

    return render(request, "auth/register_customer.html", {"form": form})


def producer_register(request):
    if request.method == "POST":
        form = ProducerRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = "producer"
            profile.address = form.cleaned_data.get("address")
            profile.postcode = form.cleaned_data.get("postcode")
            profile.farm_name = form.cleaned_data.get("farm_name")
            profile.admin_approved = True
            profile.save()

            login(request, user)
            return redirect("/")
    else:
        form = ProducerRegistrationForm()

    return render(request, "auth/register_producer.html", {"form": form})


def employee_register(request):
    if request.method == "POST":
        form = EmployeeRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.is_active = False
            user.save()

            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = form.cleaned_data["role"]
            profile.admin_approved = False
            profile.save()

            messages.success(
                request,
                "Account request submitted. An admin must approve your account before you can log in."
            )
            return redirect("login")
    else:
        form = EmployeeRegistrationForm()

    return render(request, "auth/register_employee.html", {"form": form})


@staff_member_required
def pending_employees(request):
    profiles = UserProfile.objects.filter(
        role__in=["ai_engineer", "manager"],
        admin_approved=False
    )

    return render(request, "auth/pending_employees.html", {"profiles": profiles})


@staff_member_required
def approve_employee(request, profile_id):
    profile = get_object_or_404(UserProfile, id=profile_id)

    profile.admin_approved = True
    profile.user.is_active = True

    profile.save()
    profile.user.save()

    messages.success(request, "Employee account approved.")
    return redirect("pending_employees")