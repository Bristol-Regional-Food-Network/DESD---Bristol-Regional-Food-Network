from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegistrationForm
from .models import UserProfile


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = form.cleaned_data['role']
            profile.address = form.cleaned_data.get('address')
            profile.postcode = form.cleaned_data.get('postcode')
            profile.farm_name = form.cleaned_data.get('farm_name')

            profile.save()

            login(request, user)
            return redirect('/')
    else:
        form = RegistrationForm()

    return render(request, 'auth/register.html', {'form': form})