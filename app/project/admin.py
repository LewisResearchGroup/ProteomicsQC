from django.contrib import admin

from .models import Project


# class MemberShipInline(admin.TabularInline):
#    model = Project.users.through


class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("pk", "path", "slug", "created", "path_exists", "created_by")
    list_display = ("pk", "name", "path", "path_exists", "created_by", "created")

    # inlines = [
    #    MemberShipInline,
    # ]

    filter_horizontal = ("users",)


admin.site.register(Project, ProjectAdmin)
