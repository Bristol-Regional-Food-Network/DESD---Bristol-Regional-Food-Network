from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from users.models import UserProfile

@login_required
def post_login_redirect(request):
    """
    Redirect users after login based on their role.
    Producer -> producer dashboard
    Customer -> home (or product list if you prefer)
    """
    profile = UserProfile.objects.filter(user=request.user).first()

    if profile and profile.role == "producer":
        return redirect("producer_dashboard")

    return redirect("home")