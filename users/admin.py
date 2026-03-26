from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class CustomUserAdmin(admin.ModelAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'get_role', 'email')
    search_fields = ('username', 'email', 'userprofile__role')
    list_filter = ('userprofile__role',)

    def get_role(self, obj):
        return obj.userprofile.role
    get_role.short_description = 'Role'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
