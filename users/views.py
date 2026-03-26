from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegistrationForm
from .models import UserProfile
from producers.models import Producer


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = form.cleaned_data['role']
            profile.save()

            if profile.role == "producer":
                Producer.objects.get_or_create(
                    user=user,
                    defaults={
                        "display_name": user.username,
                        "bio": "",
                        "location": "",
                        "phone": "",
                        "website": "",
                    },
                )

            login(request, user)
            return redirect('/')
    else:
        form = RegistrationForm()

    return render(request, 'auth/register.html', {'form': form})