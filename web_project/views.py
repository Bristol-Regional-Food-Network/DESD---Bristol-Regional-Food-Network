from django.shortcuts import render

# Simple home view that displays a welcome message and the user's username if they are logged in
def home(request):
    profile = None
    # Check if the user is authenticated and get their profile to display on the home page
    if request.user.is_authenticated:
        profile = request.user.userprofile
    return render(request, 'home.html', {'profile': profile})