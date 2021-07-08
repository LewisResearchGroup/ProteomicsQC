from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
#from django.contrib.auth.models import User
from .models import User
from django.conf import settings

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'is_staff', 'is_superuser')
    readonly_fields = ('last_login', 'date_joined')
    ordering = ('email',)
    fieldsets = (
        ('Fields', 
            {'fields': ('email', 'uuid', 'date_joined', 'last_login', 'is_active', 'is_staff', 
                        'is_superuser', 'groups', 'user_permissions', 'password') 
            }
        ),
    )

admin.site.register(User, CustomUserAdmin)
