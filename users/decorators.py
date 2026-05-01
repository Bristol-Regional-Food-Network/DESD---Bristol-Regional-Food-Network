from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# Custom decorator to check if the user has the required role before accessing a view
def role_required(required_role):
    def decorator(view_func):
        @login_required
        # Wrapper function that checks the user's role and redirects to login
        def wrapper(request, *args, **kwargs):
            user_role = request.user.userprofile.role
            if user_role == 'manager':
                return view_func(request, *args, **kwargs)
            
            if user_role != required_role:
                return redirect('login')
            
            # If the user has the required role, call the original view function
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator