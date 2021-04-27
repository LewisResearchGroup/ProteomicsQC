from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
#from django.contrib.auth.models import User
from .models import User
from django.conf import settings

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'is_staff')
    ordering = ('email', )
    #list_select_related = ('profile', )

admin.site.register(User, CustomUserAdmin)
