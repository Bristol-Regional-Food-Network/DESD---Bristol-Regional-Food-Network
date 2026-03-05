from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

@login_required
def post_login_redirect(request):
    # If using UserProfile.role
    profile = getattr(request.user, "userprofile", None)
    role = getattr(profile, "role", "customer")

    if role == "producer":
        return redirect("producer_dashboard")  # <-- create this url name
    return redirect("home")  # or redirect("products_list")