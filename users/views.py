from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from .forms import RegistrationForm
from .models import UserProfile
from .decorators import role_required

# View for user registration that handles both GET and POST requests
def register(request):
    if request.method == 'POST':
        # Create a registration form instance with the POST data
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set the user's password using the cleaned data from the form and save the user
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Create a user profile with the role from the form and link it
            UserProfile.objects.create(
                user=user,
                role=form.cleaned_data['role']
            )

            # Log the user in and redirect to the home page
            login(request, user)
            return redirect('/')
    else:
        # If the request method is GET, create an empty registration form
        form = RegistrationForm()

    # Render the registration template with the form context
    return render(request, 'register.html', {'form': form})

# Example views that require specific roles to access, using the custom role_required decorator
# The producer_test_page view can only be accessed by users with the 'producer' role
@role_required('producer')
def producer_test_page(request):
    return render(request, 'producer_test.html')
# The customer_test_page view can only be accessed by users with the 'customer' role
@role_required('customer')
def customer_test_page(request):
    return render(request, 'customer_test.html')
