from django.contrib import admin

# Register your models here.

from django_plotly_dash.models import DashApp, StatelessApp

admin.site.unregister(DashApp)
admin.site.unregister(StatelessApp)
