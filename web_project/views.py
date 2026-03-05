from django.shortcuts import render
from django.contrib.auth.models import AnonymousUser


# Simple home view that displays a welcome message and the user's username if they are logged in
def home(request):
    profile = None
    # Check if the user is authenticated and safely get their profile (may not exist)
    user = getattr(request, 'user', None)
    if user and not isinstance(user, AnonymousUser) and user.is_authenticated:
        # some users may not have a related UserProfile; avoid raising a 500
        try:
            profile = user.userprofile
        except Exception:
            profile = None
    return render(request, 'home.html', {'profile': profile})