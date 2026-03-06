from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegistrationForm
from .models import UserProfile
from .decorators import role_required

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            # IMPORTANT: Only do this if your form doesn't already handle password hashing
            user.set_password(form.cleaned_data['password'])
            user.save()

            # ✅ FIX: don't create twice (signals may already create it)
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = form.cleaned_data['role']
            profile.save()

            login(request, user)
            return redirect('/')  # or redirect("home") if you have name="home"
    else:
        form = RegistrationForm()

    return render(request, 'auth/register.html', {'form': form})


@role_required('producer')
def producer_test_page(request):
    return render(request, 'producer_test.html')


@role_required('customer')
def customer_test_page(request):
    return render(request, 'customer_test.html')