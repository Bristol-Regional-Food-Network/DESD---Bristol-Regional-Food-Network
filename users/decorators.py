from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def role_required(required_role):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            profile = getattr(request.user, "userprofile", None)
            if not profile or profile.role != required_role:
                return redirect("login")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator