from django import template

register = template.Library()


@register.filter
def is_admin(user):
    """Return True if user has a UserProfile with role 'admin'."""
    try:
        return bool(user and getattr(user, "userprofile", None) and user.userprofile.role == "admin")
    except Exception:
        return False


@register.filter
def is_customer(user):
    """Return True if user has a UserProfile with role 'customer'."""
    try:
        return bool(user and getattr(user, "userprofile", None) and user.userprofile.role == "customer")
    except Exception:
        return False
