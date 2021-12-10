from django.contrib import admin

from .models import Project


class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("pk", "path", "slug", "created", "path_exists", "created_by")
    list_display = ("pk", "name", "path", "path_exists", "created_by", "created")


admin.site.register(Project, ProjectAdmin)
