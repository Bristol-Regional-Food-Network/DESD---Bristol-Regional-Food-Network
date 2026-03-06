from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


@login_required
def post_login_redirect(request):
    if request.user.userprofile.role == "producer":
        return redirect("home")
    elif request.user.userprofile.role == "customer":
        return redirect("home")
    return redirect("home")