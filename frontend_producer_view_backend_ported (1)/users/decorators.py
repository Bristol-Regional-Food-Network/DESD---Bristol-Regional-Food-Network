from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# Custom decorator to check if the user has the required role before accessing a view
def role_required(required_role):
    def decorator(view_func):
        @login_required
        # Wrapper function that checks the user's role and redirects to login
        def wrapper(request, *args, **kwargs):
            if request.user.userprofile.role != required_role:
                return redirect('login')
            # If the user has the required role, call the original view function
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator